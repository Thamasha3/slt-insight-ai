"""Singleton system settings stored in MongoDB. Admin is the only writer."""

from datetime import datetime, timezone

from app.database.connection import system_settings_collection

SETTINGS_DOCUMENT_ID = "global"
DEFAULT_CHAT_HISTORY_RETENTION_DAYS = 90
DEFAULT_ADMIN_CHAT_ENABLED = False


def _defaults() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "_id": SETTINGS_DOCUMENT_ID,
        "chat_history_retention_days": DEFAULT_CHAT_HISTORY_RETENTION_DAYS,
        "admin_chat_enabled": DEFAULT_ADMIN_CHAT_ENABLED,
        "updated_at": now,
    }


def settings_public_view(document: dict) -> dict:
    return {
        "chat_history_retention_days": int(document.get("chat_history_retention_days") or DEFAULT_CHAT_HISTORY_RETENTION_DAYS),
        "admin_chat_enabled": bool(document.get("admin_chat_enabled")),
        "updated_at": document.get("updated_at"),
    }


async def get_system_settings() -> dict:
    collection = system_settings_collection()
    document = await collection.find_one({"_id": SETTINGS_DOCUMENT_ID})
    if document is None:
        document = _defaults()
        await collection.insert_one(document)
    return document


async def update_system_settings(*, chat_history_retention_days: int | None, admin_chat_enabled: bool | None) -> dict:
    current = await get_system_settings()
    updates: dict = {"updated_at": datetime.now(timezone.utc)}
    if chat_history_retention_days is not None:
        updates["chat_history_retention_days"] = chat_history_retention_days
    if admin_chat_enabled is not None:
        updates["admin_chat_enabled"] = admin_chat_enabled
    await system_settings_collection().update_one({"_id": SETTINGS_DOCUMENT_ID}, {"$set": updates})
    return await get_system_settings()
