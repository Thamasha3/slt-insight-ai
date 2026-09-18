"""Admin-only system configuration (chat retention and Admin chatbot access)."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.rbac import CurrentUser, require_roles
from app.models.audit import AuditAction
from app.models.user import Role
from app.schemas.settings import SystemSettingsOut, SystemSettingsUpdateRequest
from app.services.system_settings import get_system_settings, settings_public_view, update_system_settings
from app.utils.audit import write_audit_log

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


def _to_out(document: dict) -> SystemSettingsOut:
    return SystemSettingsOut(**settings_public_view(document))


@router.get("", response_model=SystemSettingsOut)
async def get_settings(_admin: CurrentUser = Depends(require_roles(Role.ADMIN))):
    return _to_out(await get_system_settings())


@router.put("", response_model=SystemSettingsOut)
async def put_settings(
    payload: SystemSettingsUpdateRequest,
    admin: CurrentUser = Depends(require_roles(Role.ADMIN)),
):
    if payload.chat_history_retention_days is None and payload.admin_chat_enabled is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide chat_history_retention_days and/or admin_chat_enabled.",
        )
    document = await update_system_settings(
        chat_history_retention_days=payload.chat_history_retention_days,
        admin_chat_enabled=payload.admin_chat_enabled,
    )
    await write_audit_log(
        user_id=admin.id,
        action=AuditAction.SETTINGS_UPDATED.value,
        resource="system-settings",
        status_="SUCCESS",
    )
    return _to_out(document)
