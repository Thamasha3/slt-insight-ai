import pytest

from app.auth.security import hash_password
from app.database.connection import users_collection
from app.models.user import Role, UserStatus, new_user_document


async def _insert_user(*, email: str, password: str, role: Role):
    document = new_user_document(
        name="Test",
        email=email,
        password_hash=hash_password(password),
        role=role,
        region=None,
        status=UserStatus.ACTIVE,
    )
    await users_collection().insert_one(document)


async def _login(client, email: str, password: str) -> str:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_normal_user_cannot_read_admin_stats(client):
    await _insert_user(email="normal@example.com", password="Password123", role=Role.NORMAL)
    token = await _login(client, "normal@example.com", "Password123")
    response = await client.get("/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_read_stats(client):
    await _insert_user(email="admin1@example.com", password="AdminPass123", role=Role.ADMIN)
    token = await _login(client, "admin1@example.com", "AdminPass123")
    response = await client.get("/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["users_total"] >= 1
    assert "GENERAL" in body["knowledge_by_category"]


@pytest.mark.asyncio
async def test_admin_can_export_audit_logs_csv(client):
    await _insert_user(email="admin1@example.com", password="AdminPass123", role=Role.ADMIN)
    token = await _login(client, "admin1@example.com", "AdminPass123")
    headers = {"Authorization": f"Bearer {token}"}
    await client.get("/admin/users", headers=headers)

    response = await client.get("/admin/audit-logs/export", headers=headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    text = response.content.decode("utf-8-sig")
    assert text.startswith("timestamp,user_id,action,resource,status")
    assert "AUDIT_EXPORTED" not in text.splitlines()[0]


@pytest.mark.asyncio
async def test_super_user_cannot_export_or_list_audit_logs(client):
    await _insert_user(email="super@example.com", password="Password123", role=Role.SUPER)
    token = await _login(client, "super@example.com", "Password123")
    headers = {"Authorization": f"Bearer {token}"}
    listed = await client.get("/admin/audit-logs", headers=headers)
    exported = await client.get("/admin/audit-logs/export", headers=headers)
    users = await client.get("/admin/users", headers=headers)
    stats = await client.get("/admin/stats", headers=headers)
    assert listed.status_code == 403
    assert exported.status_code == 403
    assert users.status_code == 403
    assert stats.status_code == 403
