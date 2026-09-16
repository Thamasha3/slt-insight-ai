"""MongoDB indexes. Safe to run on every startup (idempotent)."""

from app.database.connection import (
    audit_logs_collection,
    chat_messages_collection,
    chat_sessions_collection,
    document_chunks_collection,
    documents_collection,
    users_collection,
)


async def create_indexes() -> None:
    await users_collection().create_index("email", unique=True)
    await users_collection().create_index("role")
    await users_collection().create_index("status")

    await documents_collection().create_index("category")
    await documents_collection().create_index("region")
    await documents_collection().create_index("status")

    await document_chunks_collection().create_index("document_id")
    await document_chunks_collection().create_index("category")
    await document_chunks_collection().create_index("region")
    await document_chunks_collection().create_index("status")

    await chat_sessions_collection().create_index("user_id")
    await chat_messages_collection().create_index("session_id")
    await chat_messages_collection().create_index("user_id")

    await audit_logs_collection().create_index("user_id")
    await audit_logs_collection().create_index("timestamp")
