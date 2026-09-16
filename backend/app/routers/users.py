"""Current-user profile endpoints (spec: GET/PUT /users/me)."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends

from app.auth.rbac import CurrentUser, get_current_user
from app.database.connection import users_collection
from app.models.audit import AuditAction
from app.schemas.auth import CurrentUserResponse
from app.schemas.user import UpdateOwnProfileRequest
from app.utils.audit import write_audit_log

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return CurrentUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        region=user.region,
        status=user.status,
    )


@router.put("/me", response_model=CurrentUserResponse)
async def update_me(payload: UpdateOwnProfileRequest, user: CurrentUser = Depends(get_current_user)):
    updates: dict = {}
    if payload.name is not None and payload.name.strip():
        updates["name"] = payload.name.strip()

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await users_collection().update_one({"_id": ObjectId(user.id)}, {"$set": updates})
        await write_audit_log(
            user_id=user.id,
            action=AuditAction.USER_UPDATED.value,
            resource="users/me",
            status_="SUCCESS",
        )

    document = await users_collection().find_one({"_id": ObjectId(user.id)})
    return CurrentUserResponse(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        role=document["role"],
        region=document.get("region"),
        status=document["status"],
    )
