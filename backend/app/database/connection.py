"""
MongoDB connection using Motor (async driver).

One client is created on FastAPI startup and closed on shutdown.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config.settings import get_settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def connect_to_mongo() -> None:
    global _client, _db
    if _client is not None:
        return
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.mongodb_database]


def connect_with_client(client: AsyncIOMotorClient, database_name: str) -> None:
    """Used by tests to inject a mock MongoDB client."""
    global _client, _db
    _client = client
    _db = client[database_name]


def close_mongo_connection() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized. Did startup run?")
    return _db


def users_collection():
    return get_db()["users"]


def documents_collection():
    return get_db()["documents"]


def document_chunks_collection():
    return get_db()["document_chunks"]


def knowledge_sources_collection():
    return get_db()["knowledge_sources"]


def approval_records_collection():
    return get_db()["approval_records"]


def chat_sessions_collection():
    return get_db()["chat_sessions"]


def chat_messages_collection():
    return get_db()["chat_messages"]


def audit_logs_collection():
    return get_db()["audit_logs"]


def system_settings_collection():
    return get_db()["system_settings"]
