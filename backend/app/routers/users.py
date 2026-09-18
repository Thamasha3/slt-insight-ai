"""Current-user profile endpoints (spec: GET/PUT /users/me)."""

from datetime import datetime, timezone
from pathlib import Path
import re

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.auth.rbac import CurrentUser, get_current_user
from app.config.settings import get_settings
from app.database.connection import users_collection
from app.models.audit import AuditAction
from app.schemas.auth import CurrentUserResponse
from app.schemas.user import UpdateOwnProfileRequest
from app.utils.audit import write_audit_log

router = APIRouter(prefix="/users", tags=["users"])

AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
AVATAR_FILENAME = re.compile(r"^[a-f0-9]{24}\.(jpg|png|webp|gif)$")
MAX_AVATAR_BYTES = 5 * 1024 * 1024


def _user_out(document: dict) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=str(document["_id"]),
        name=document["name"],
        email=document["email"],
        role=document["role"],
        region=document.get("region"),
        status=document["status"],
        avatar_url=document.get("avatar_url"),
    )


def _avatars_dir() -> Path:
    path = Path(get_settings().upload_dir) / "avatars"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return CurrentUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        region=user.region,
        status=user.status,
        avatar_url=user.avatar_url,
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
    return _user_out(document)


@router.post("/me/avatar", response_model=CurrentUserResponse)
async def update_my_avatar(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    content_type = (file.content_type or "").lower()
    suffix = AVATAR_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile pictures must be JPEG, PNG, WebP, or GIF.",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty.")
    if len(payload) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile pictures must be 5 MB or smaller.")

    avatars = _avatars_dir()
    for old in avatars.glob(f"{user.id}.*"):
        old.unlink(missing_ok=True)

    stored = avatars / f"{user.id}{suffix}"
    stored.write_bytes(payload)
    stamp = int(datetime.now(timezone.utc).timestamp())
    avatar_url = f"/users/avatars/{stored.name}?v={stamp}"

    await users_collection().update_one(
        {"_id": ObjectId(user.id)},
        {"$set": {"avatar_url": avatar_url, "updated_at": datetime.now(timezone.utc)}},
    )
    await write_audit_log(
        user_id=user.id,
        action=AuditAction.USER_UPDATED.value,
        resource="users/me/avatar",
        status_="SUCCESS",
    )
    document = await users_collection().find_one({"_id": ObjectId(user.id)})
    return _user_out(document)


@router.get("/avatars/{filename}")
async def get_avatar(filename: str):
    name = filename.strip().lower()
    if not AVATAR_FILENAME.match(name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found.")
    path = _avatars_dir() / name
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found.")
    media = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
    return FileResponse(path, media_type=media.get(path.suffix, "application/octet-stream"))
