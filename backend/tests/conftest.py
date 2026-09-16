import os

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DATABASE", "insight_ai_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ADMIN_EMAIL_1", "admin1@example.com")
os.environ.setdefault("ADMIN_EMAIL_2", "admin2@example.com")

from app.config.settings import get_settings
from app.database.connection import connect_with_client

get_settings.cache_clear()


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    mock = AsyncMongoMockClient()
    connect_with_client(mock, "insight_ai_test")

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
