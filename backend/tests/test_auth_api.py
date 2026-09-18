import pytest

from app.auth.security import hash_password
from app.database.connection import users_collection
from app.models.user import Role, UserStatus, new_user_document


async def _insert_user(*, name: str, email: str, password: str, role: Role, status: UserStatus, region=None):
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


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_creates_pending_normal_account(client):
    response = await client.post(
        "/auth/register",
        json={
            "name": "Test Employee",
            "email": "employee1@slt.com.lk",
            "password": "Password123",
            "requested_region": "SOUTHERN",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"

    login = await client.post(
        "/auth/login",
        json={"email": "employee1@slt.com.lk", "password": "Password123"},
    )
    assert login.status_code == 403
    assert "pending" in login.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_rejects_admin_email(client):
    response = await client.post(
        "/auth/register",
        json={"name": "Hacker", "email": "admin1@example.com", "password": "Password123"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_has_no_role_field(client):
    response = await client.post(
        "/auth/register",
        json={
            "name": "Hacker",
            "email": "hacker@example.com",
            "password": "Password123",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_super_user_cannot_call_admin_api(client):
    await _insert_user(
        name="Super",
        email="super@example.com",
        password="Password123",
        role=Role.SUPER,
        status=UserStatus.ACTIVE,
    )
    login = await client.post("/auth/login", json={"email": "super@example.com", "password": "Password123"})
    token = login.json()["access_token"]
    response = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_normal_user_cannot_call_admin_api(client):
    await _insert_user(
        name="Normal",
        email="normal@example.com",
        password="Password123",
        role=Role.NORMAL,
        status=UserStatus.ACTIVE,
    )
    login = await client.post("/auth/login", json={"email": "normal@example.com", "password": "Password123"})
    token = login.json()["access_token"]
    response = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_cannot_change_own_role_via_profile(client):
    await _insert_user(
        name="Normal",
        email="normal2@example.com",
        password="Password123",
        role=Role.NORMAL,
        status=UserStatus.ACTIVE,
    )
    login = await client.post("/auth/login", json={"email": "normal2@example.com", "password": "Password123"})
    token = login.json()["access_token"]
    response = await client.put(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Name", "role": "ADMIN"},
    )
    assert response.status_code == 422
    me = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "NORMAL"
    assert me.json()["name"] == "Normal"


@pytest.mark.asyncio
async def test_admin_cannot_assign_admin_role_to_non_allowlisted_email(client):
    await _insert_user(
        name="Admin",
        email="admin1@example.com",
        password="AdminPass123",
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    user_id = await _insert_user(
        name="Employee",
        email="employee@example.com",
        password="Password123",
        role=Role.NORMAL,
        status=UserStatus.ACTIVE,
    )
    login = await client.post("/auth/login", json={"email": "admin1@example.com", "password": "AdminPass123"})
    token = login.json()["access_token"]
    response = await client.put(
        f"/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "ADMIN"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_can_list_users(client):
    await _insert_user(
        name="Admin",
        email="admin1@example.com",
        password="AdminPass123",
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    login = await client.post("/auth/login", json={"email": "admin1@example.com", "password": "AdminPass123"})
    token = login.json()["access_token"]
    response = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_admin_approve_pending_regional(client):
    await _insert_user(
        name="Admin",
        email="admin1@example.com",
        password="AdminPass123",
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    user_id = await _insert_user(
        name="Pending",
        email="pending@example.com",
        password="Password123",
        role=Role.NORMAL,
        status=UserStatus.PENDING,
        region="SOUTHERN",
    )
    login = await client.post("/auth/login", json={"email": "admin1@example.com", "password": "AdminPass123"})
    token = login.json()["access_token"]
    response = await client.post(
        f"/admin/users/{user_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "REGIONAL", "region": "SOUTHERN"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["role"] == "REGIONAL"

    employee_login = await client.post(
        "/auth/login",
        json={"email": "pending@example.com", "password": "Password123"},
    )
    assert employee_login.status_code == 200
