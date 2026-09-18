from datetime import datetime, timedelta, timezone

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
async def test_admin_can_filter_audit_logs_by_action_and_user(client):
    await _insert_user(email="admin1@example.com", password="AdminPass123", role=Role.ADMIN)
    token = await _login(client, "admin1@example.com", "AdminPass123")
    headers = {"Authorization": f"Bearer {token}"}

    users = await client.get("/admin/users", headers=headers)
    admin_id = users.json()[0]["id"]

    by_action = await client.get("/admin/audit-logs", headers=headers, params={"action_type": "LOGIN"})
    assert by_action.status_code == 200
    assert by_action.json()
    assert all(row["action"] == "LOGIN" for row in by_action.json())

    by_user = await client.get("/admin/audit-logs", headers=headers, params={"user_id": admin_id})
    assert by_user.status_code == 200
    assert by_user.json()
    assert all(row["user_id"] == admin_id for row in by_user.json())

    start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    by_date = await client.get(
        "/admin/audit-logs",
        headers=headers,
        params={"start_date": start, "end_date": end},
    )
    assert by_date.status_code == 200
    assert by_date.json()

    future_start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    empty = await client.get(
        "/admin/audit-logs",
        headers=headers,
        params={"start_date": future_start},
    )
    assert empty.status_code == 200
    assert empty.json() == []
