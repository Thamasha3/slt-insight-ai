from datetime import datetime, timedelta, timezone

import pytest

from app.auth.security import hash_password
from app.database.connection import users_collection
from app.models.user import Role, UserStatus, new_user_document
from app.auth.rbac import CurrentUser, allowed_categories_for


async def _insert_user(*, email: str, password: str, role: Role):
    document = new_user_document(
        name="Test",
        email=email,
        password_hash=hash_password(password),
        role=role,
        region=None,
        status=UserStatus.ACTIVE,
    )
    result = await users_collection().insert_one(document)
    return str(result.inserted_id)


async def _login(client, email: str, password: str) -> str:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _admin_user() -> CurrentUser:
    return CurrentUser(
        {
            "_id": "000000000000000000000001",
            "name": "Admin",
            "email": "admin1@example.com",
            "role": Role.ADMIN.value,
            "region": None,
            "status": UserStatus.ACTIVE.value,
        }
    )


def test_admin_categories_remain_empty_until_chat_enabled():
    assert allowed_categories_for(_admin_user()) == set()
    assert "GENERAL" in allowed_categories_for(_admin_user(), admin_chat_enabled=True)


@pytest.mark.asyncio
async def test_admin_can_get_and_put_system_settings(client):
    await _insert_user(email="admin1@example.com", password="AdminPass123", role=Role.ADMIN)
    token = await _login(client, "admin1@example.com", "AdminPass123")
    headers = {"Authorization": f"Bearer {token}"}

    initial = await client.get("/admin/settings", headers=headers)
    assert initial.status_code == 200
    body = initial.json()
    assert body["admin_chat_enabled"] is False
    assert body["chat_history_retention_days"] == 90

    updated = await client.put(
        "/admin/settings",
        headers=headers,
        json={"chat_history_retention_days": 30, "admin_chat_enabled": True},
    )
    assert updated.status_code == 200
    assert updated.json()["chat_history_retention_days"] == 30
    assert updated.json()["admin_chat_enabled"] is True

    reread = await client.get("/admin/settings", headers=headers)
    assert reread.json()["chat_history_retention_days"] == 30
    assert reread.json()["admin_chat_enabled"] is True


@pytest.mark.asyncio
async def test_super_user_cannot_access_system_settings(client):
    await _insert_user(email="super@example.com", password="Password123", role=Role.SUPER)
    token = await _login(client, "super@example.com", "Password123")
    headers = {"Authorization": f"Bearer {token}"}
    listed = await client.get("/admin/settings", headers=headers)
    updated = await client.put("/admin/settings", headers=headers, json={"admin_chat_enabled": True})
    assert listed.status_code == 403
    assert updated.status_code == 403


@pytest.mark.asyncio
async def test_admin_chat_allowed_when_setting_enabled(client, monkeypatch):
    from app.services.rag import chat as chat_service

    monkeypatch.setattr(chat_service, "generate_answer", lambda **_: "Leave is requested through HR. [1]")
    await _insert_user(email="admin1@example.com", password="AdminPass123", role=Role.ADMIN)
    token = await _login(client, "admin1@example.com", "AdminPass123")
    headers = {"Authorization": f"Bearer {token}"}

    from app.database.connection import document_chunks_collection

    await document_chunks_collection().insert_one(
        {
            "document_id": "doc-general",
            "content": "Sample leave policy: employees may request annual leave through HR.",
            "category": "GENERAL",
            "region": None,
            "filename": "hr_policy.pdf",
            "source_page": 1,
            "source_row": None,
            "sheet_name": None,
            "status": "APPROVED",
            "chunk_index": 0,
        }
    )

    enabled = await client.put("/admin/settings", headers=headers, json={"admin_chat_enabled": True})
    assert enabled.status_code == 200

    response = await client.post("/chat", headers=headers, json={"query": "annual leave policy"})
    assert response.status_code == 200
    assert response.json()["gemini_called"] is True
    assert response.json()["insufficient_evidence"] is False
    assert "GENERAL" in response.json()["allowed_categories"]


@pytest.mark.asyncio
async def test_chat_sessions_respect_retention_setting(client):
    await _insert_user(email="normal@example.com", password="Password123", role=Role.NORMAL)
    await _insert_user(email="admin1@example.com", password="AdminPass123", role=Role.ADMIN)
    admin_token = await _login(client, "admin1@example.com", "AdminPass123")
    await client.put(
        "/admin/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"chat_history_retention_days": 7},
    )

    token = await _login(client, "normal@example.com", "Password123")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/chat", headers=headers, json={"query": "hello"})
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    from app.database.connection import chat_sessions_collection
    from bson import ObjectId

    await chat_sessions_collection().update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"updated_at": datetime.now(timezone.utc) - timedelta(days=30)}},
    )

    listed = await client.get("/chat/sessions", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []
