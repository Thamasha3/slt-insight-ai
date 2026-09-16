"""Admin-only user management. Gated by require_roles(Role.ADMIN)."""

import csv
from datetime import datetime, timezone
from io import StringIO

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.auth.rbac import CurrentUser, require_roles
from app.auth.security import hash_password
from app.config.settings import get_settings
from app.database.connection import (
    audit_logs_collection,
    document_chunks_collection,
    documents_collection,
    users_collection,
)
from app.models.audit import AuditAction
from app.models.document import DocumentStatus, KnowledgeCategory
from app.models.user import Role, UserStatus, new_user_document
from app.schemas.admin import AdminStatsOut
from app.schemas.user import AdminCreateUserRequest, AdminUpdateUserRequest, ApprovalDecisionRequest, UserOut
from app.utils.audit import write_audit_log

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_user_out(document: dict) -> UserOut:
    return UserOut(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        role=document["role"],
        region=document.get("region"),
        status=document["status"],
    )


def assert_role_assignment_allowed(target_email: str, requested_role: Role) -> None:
    if requested_role != Role.ADMIN:
        return
    settings = get_settings()
    if target_email.strip().lower() not in settings.admin_emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The ADMIN role can only be assigned to a pre-approved SLT administrator email.",
        )


@router.get("/stats", response_model=AdminStatsOut)
async def admin_stats(_admin: CurrentUser = Depends(require_roles(Role.ADMIN))):
    users = users_collection()
    documents = documents_collection()
    chunks = document_chunks_collection()
    by_category: dict[str, int] = {}
    for category in KnowledgeCategory:
        by_category[category.value] = await documents.count_documents({"category": category.value})
    return AdminStatsOut(
        users_total=await users.count_documents({}),
        users_pending=await users.count_documents({"status": UserStatus.PENDING.value}),
        users_active=await users.count_documents({"status": UserStatus.ACTIVE.value}),
        documents_total=await documents.count_documents({}),
        documents_pending=await documents.count_documents({"status": DocumentStatus.PENDING.value}),
        documents_approved=await documents.count_documents({"status": DocumentStatus.APPROVED.value}),
        documents_rejected=await documents.count_documents({"status": DocumentStatus.REJECTED.value}),
        documents_failed=await documents.count_documents({"status": DocumentStatus.FAILED.value}),
        chunks_approved=await chunks.count_documents({"status": DocumentStatus.APPROVED.value}),
        knowledge_by_category=by_category,
    )


@router.get("/users", response_model=list[UserOut])
async def list_users(_admin: CurrentUser = Depends(require_roles(Role.ADMIN))):
    cursor = users_collection().find({})
    return [_to_user_out(document) async for document in cursor]


@router.get("/users/pending", response_model=list[UserOut])
async def list_pending_users(_admin: CurrentUser = Depends(require_roles(Role.ADMIN))):
    cursor = users_collection().find({"status": UserStatus.PENDING.value})
    return [_to_user_out(document) async for document in cursor]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminCreateUserRequest,
    admin: CurrentUser = Depends(require_roles(Role.ADMIN)),
):
    email = payload.email.strip().lower()
    assert_role_assignment_allowed(email, payload.role)

    if payload.role == Role.REGIONAL and payload.region is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Regional users must have a region")

    existing = await users_collection().find_one({"email": email})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    document = new_user_document(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        region=payload.region.value if payload.region else None,
        status=UserStatus.ACTIVE,
    )
    result = await users_collection().insert_one(document)
    await write_audit_log(
        user_id=admin.id,
        action=AuditAction.USER_UPDATED.value,
        resource=f"users/{result.inserted_id}",
        status_="CREATED",
    )
    created = await users_collection().find_one({"_id": result.inserted_id})
    return _to_user_out(created)


@router.post("/users/{user_id}/approve", response_model=UserOut)
async def approve_user(
    user_id: str,
    payload: ApprovalDecisionRequest,
    admin: CurrentUser = Depends(require_roles(Role.ADMIN)),
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id")

    target = await users_collection().find_one({"_id": ObjectId(user_id)})
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target["status"] != UserStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not pending approval")

    assert_role_assignment_allowed(target["email"], payload.role)

    if payload.role == Role.REGIONAL and payload.region is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Regional users must have a region")
    if payload.role == Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Do not approve registrations as ADMIN. Provision administrators with the bootstrap script or POST /admin/users.",
        )

    updates = {
        "role": payload.role.value,
        "region": payload.region.value if payload.region else None,
        "status": UserStatus.ACTIVE.value,
        "updated_at": datetime.now(timezone.utc),
    }
    await users_collection().update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    await write_audit_log(
        user_id=admin.id,
        action=AuditAction.ACCOUNT_APPROVED.value,
        resource=f"users/{user_id}",
        status_="SUCCESS",
    )
    document = await users_collection().find_one({"_id": ObjectId(user_id)})
    return _to_user_out(document)


@router.post("/users/{user_id}/reject", response_model=UserOut)
async def reject_user(user_id: str, admin: CurrentUser = Depends(require_roles(Role.ADMIN))):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id")

    target = await users_collection().find_one({"_id": ObjectId(user_id)})
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target["status"] != UserStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not pending approval")

    await users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status": UserStatus.REJECTED.value, "updated_at": datetime.now(timezone.utc)}},
    )
    await write_audit_log(
        user_id=admin.id,
        action=AuditAction.ACCOUNT_REJECTED.value,
        resource=f"users/{user_id}",
        status_="SUCCESS",
    )
    document = await users_collection().find_one({"_id": ObjectId(user_id)})
    return _to_user_out(document)


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    payload: AdminUpdateUserRequest,
    admin: CurrentUser = Depends(require_roles(Role.ADMIN)),
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id")

    target = await users_collection().find_one({"_id": ObjectId(user_id)})
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updates: dict = {}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.role is not None:
        assert_role_assignment_allowed(target["email"], payload.role)
        updates["role"] = payload.role.value
    if payload.region is not None:
        updates["region"] = payload.region.value
    if payload.status is not None:
        updates["status"] = payload.status.value

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await users_collection().update_one({"_id": ObjectId(user_id)}, {"$set": updates})
        action = AuditAction.ROLE_CHANGED.value if "role" in updates else AuditAction.USER_UPDATED.value
        await write_audit_log(user_id=admin.id, action=action, resource=f"users/{user_id}", status_="SUCCESS")

    document = await users_collection().find_one({"_id": ObjectId(user_id)})
    return _to_user_out(document)


@router.delete("/users/{user_id}")
async def deactivate_user(user_id: str, admin: CurrentUser = Depends(require_roles(Role.ADMIN))):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id")

    result = await users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"status": UserStatus.DEACTIVATED.value, "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await write_audit_log(
        user_id=admin.id,
        action=AuditAction.USER_DEACTIVATED.value,
        resource=f"users/{user_id}",
        status_="SUCCESS",
    )
    return {"message": "User deactivated"}


def _audit_row(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "user_id": document.get("user_id"),
        "action": document.get("action"),
        "resource": document.get("resource"),
        "status": document.get("status"),
        "timestamp": document.get("timestamp"),
    }


@router.get("/audit-logs/export")
async def export_audit_logs(admin: CurrentUser = Depends(require_roles(Role.ADMIN)), limit: int = 10000):
    cursor = audit_logs_collection().find({}).sort("timestamp", -1).limit(min(max(limit, 1), 20000))
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["timestamp", "user_id", "action", "resource", "status"])
    async for document in cursor:
        row = _audit_row(document)
        writer.writerow(
            [
                row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else row["timestamp"],
                row["user_id"] or "",
                row["action"] or "",
                row["resource"] or "",
                row["status"] or "",
            ]
        )
    await write_audit_log(
        user_id=admin.id,
        action=AuditAction.AUDIT_EXPORTED.value,
        resource="audit-logs",
        status_="SUCCESS",
    )
    filename = f"audit-logs-{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(
        content=buffer.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit-logs")
async def list_audit_logs(_admin: CurrentUser = Depends(require_roles(Role.ADMIN)), limit: int = 100):
    cursor = audit_logs_collection().find({}).sort("timestamp", -1).limit(min(limit, 500))
    return [_audit_row(document) async for document in cursor]
