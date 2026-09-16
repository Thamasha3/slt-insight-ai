from datetime import datetime, timezone

from app.database.connection import audit_logs_collection


async def write_audit_log(*, user_id: str | None, action: str, resource: str, status_: str) -> None:
    await audit_logs_collection().insert_one(
        {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "status": status_,
            "timestamp": datetime.now(timezone.utc),
        }
    )
