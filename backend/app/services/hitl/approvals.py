"""Knowledge approval records (human-in-the-loop)."""

from datetime import datetime, timezone

from app.database.connection import approval_records_collection


async def record_knowledge_decision(*, document_id: str, admin_id: str, decision: str) -> None:
    await approval_records_collection().insert_one(
        {
            "document_id": document_id,
            "admin_id": admin_id,
            "decision": decision,
            "timestamp": datetime.now(timezone.utc),
        }
    )
