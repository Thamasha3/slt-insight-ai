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
async def test_user_can_upload_profile_avatar(client):
    await _insert_user(
        name="Thamasha Samaranayaka",
        email="thamasha@slt.com.lk",
        password="Password123",
        role=Role.NORMAL,
        status=UserStatus.ACTIVE,
    )
    login = await client.post("/auth/login", json={"email": "thamasha@slt.com.lk", "password": "Password123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    response = await client.post(
        "/users/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", png, "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["avatar_url"]
    assert "/users/avatars/" in body["avatar_url"]

    me = await client.get("/users/me", headers=headers)
    assert me.json()["avatar_url"] == body["avatar_url"]

    filename = body["avatar_url"].split("?")[0].rsplit("/", 1)[-1]
    image = await client.get(f"/users/avatars/{filename}")
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/")
