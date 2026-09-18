"""Authentication: register, login, logout, current user, profile."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.jwt import create_access_token
from app.auth.rbac import CurrentUser, get_current_user
from app.auth.security import hash_password, verify_password
from app.config.settings import get_settings
from app.database.connection import users_collection
from app.models.audit import AuditAction
from app.models.user import Role, UserStatus, new_user_document
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, is_slt_corporate_email
from app.utils.audit import write_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    settings = get_settings()
    email = payload.email.strip().lower()

    if not is_slt_corporate_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is limited to @slt.com.lk email addresses.",
        )

    if email in settings.admin_emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is reserved. Contact your system administrator.",
        )

    existing = await users_collection().find_one({"email": email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    document = new_user_document(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=Role.NORMAL,
        region=payload.requested_region.value if payload.requested_region else None,
        status=UserStatus.PENDING,
    )
    result = await users_collection().insert_one(document)

    await write_audit_log(
        user_id=str(result.inserted_id),
        action=AuditAction.REGISTER.value,
        resource="users",
        status_=UserStatus.PENDING.value,
    )

    return {
        "message": "Registration submitted. An administrator must approve your account before you can log in.",
        "status": UserStatus.PENDING.value,
    }


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    email = payload.email.strip().lower()
    document = await users_collection().find_one({"email": email})

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )

    if document is None:
        raise invalid_credentials
    if not verify_password(payload.password, document["password_hash"]):
        raise invalid_credentials

    if document["status"] == UserStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending administrator approval",
        )
    if document["status"] == UserStatus.REJECTED.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your registration was rejected")
    if document["status"] == UserStatus.DEACTIVATED.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has been deactivated")

    token = create_access_token(
        user_id=str(document["_id"]),
        email=document["email"],
        role=document["role"],
        region=document.get("region"),
        user_status=document["status"],
    )

    await write_audit_log(
        user_id=str(document["_id"]),
        action=AuditAction.LOGIN.value,
        resource="auth",
        status_="SUCCESS",
    )

    return TokenResponse(access_token=token, role=document["role"], status=document["status"])


@router.post("/logout")
async def logout(user: CurrentUser = Depends(get_current_user)):
    await write_audit_log(user_id=user.id, action=AuditAction.LOGOUT.value, resource="auth", status_="SUCCESS")
    return {"message": "Logged out"}
