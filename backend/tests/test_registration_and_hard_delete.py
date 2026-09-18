import pytest

from app.auth.security import hash_password
from app.database.connection import audit_logs_collection, users_collection
from app.models.user import Role, UserStatus, new_user_document


async def _insert_user(*, name: str, email: str, password: str, role: Role, status: UserStatus = UserStatus.ACTIVE, region=None):
    document = new_user_document(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        region=region,
        status=status,
    )
    result = await users_collection().insert_one(document)
    return str(result.inserted_id)


async def _login(client, email: str, password: str) -> str:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_register_rejects_non_slt_domain(client):
    response = await client.post(
        "/auth/register",
        json={"name": "Visitor", "email": "visitor@gmail.com", "password": "Password123"},
    )
    assert response.status_code == 400
    assert "slt.com.lk" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_rejects_lookalike_slt_domain(client):
    response = await client.post(
        "/auth/register",
        json={"name": "Visitor", "email": "visitor@slt.com.lk.example.com", "password": "Password123"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_accepts_slt_corporate_email(client):
    response = await client.post(
        "/auth/register",
        json={"name": "SLT Employee", "email": "new.hire@slt.com.lk", "password": "Password123"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"


@pytest.mark.asyncio
async def test_admin_hard_delete_removes_user_and_keeps_audit_logs(client):
    await _insert_user(
        name="Admin",
        email="admin1@example.com",
        password="AdminPass123",
        role=Role.ADMIN,
    )
    user_id = await _insert_user(
        name="Employee",
        email="employee@example.com",
        password="Password123",
        role=Role.NORMAL,
    )
    token = await _login(client, "admin1@example.com", "AdminPass123")
    headers = {"Authorization": f"Bearer {token}"}

    employee_login = await client.post(
        "/auth/login", json={"email": "employee@example.com", "password": "Password123"}
    )
    assert employee_login.status_code == 200

    deleted = await client.delete(f"/admin/users/{user_id}", headers=headers)
    assert deleted.status_code == 200

    remaining = await users_collection().find_one({"email": "employee@example.com"})
    assert remaining is None

    login_after = await client.post(
        "/auth/login", json={"email": "employee@example.com", "password": "Password123"}
    )
    assert login_after.status_code == 401

    logs = await client.get("/admin/audit-logs", headers=headers)
    assert logs.status_code == 200
    actions = {row["action"] for row in logs.json()}
    assert "LOGIN" in actions
    assert "USER_DELETED" in actions
    stored_logs = await audit_logs_collection().count_documents({"user_id": user_id})
    assert stored_logs >= 1


@pytest.mark.asyncio
async def test_admin_deactivate_endpoint_still_blocks_login(client):
    await _insert_user(
        name="Admin",
        email="admin1@example.com",
        password="AdminPass123",
        role=Role.ADMIN,
    )
    await _insert_user(
        name="Employee",
        email="employee@example.com",
        password="Password123",
        role=Role.NORMAL,
    )
    token = await _login(client, "admin1@example.com", "AdminPass123")
    users = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    employee_id = next(row["id"] for row in users.json() if row["email"] == "employee@example.com")

    response = await client.post(
        f"/admin/users/{employee_id}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    login = await client.post("/auth/login", json={"email": "employee@example.com", "password": "Password123"})
    assert login.status_code == 403
    assert "deactivat" in login.json()["detail"].lower()


@pytest.mark.asyncio
async def test_super_user_cannot_hard_delete_users(client):
    await _insert_user(name="Super", email="super@example.com", password="Password123", role=Role.SUPER)
    user_id = await _insert_user(
        name="Employee",
        email="employee@example.com",
        password="Password123",
        role=Role.NORMAL,
    )
    token = await _login(client, "super@example.com", "Password123")
    response = await client.delete(f"/admin/users/{user_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
