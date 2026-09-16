import pytest

from app.auth.security import hash_password
from app.database.connection import document_chunks_collection, users_collection
from app.models.user import Role, UserStatus, new_user_document


async def _insert_user(*, email: str, password: str, role: Role, region: str | None = None):
    document = new_user_document(
        name="Test",
        email=email,
        password_hash=hash_password(password),
        role=role,
        region=region if region is not None else ("SOUTHERN" if role == Role.REGIONAL else None),
        status=UserStatus.ACTIVE,
    )
    result = await users_collection().insert_one(document)
    return str(result.inserted_id)


async def _login(client, email: str, password: str) -> str:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


async def _seed_chunks():
    await document_chunks_collection().insert_many(
        [
            {
                "document_id": "doc-general",
                "content": "Sample leave policy: employees may request annual leave through HR.",
                "category": "GENERAL",
                "region": None,
                "filename": "hr_policy.pdf",
                "source_page": 12,
                "source_row": None,
                "sheet_name": None,
                "status": "APPROVED",
                "chunk_index": 0,
            },
            {
                "document_id": "doc-south",
                "content": "Southern region office hours in Galle are 08:00 to 16:00 on weekdays.",
                "category": "REGIONAL",
                "region": "SOUTHERN",
                "filename": "south_hours.xlsx",
                "source_page": None,
                "source_row": 2,
                "sheet_name": "Southern",
                "status": "APPROVED",
                "chunk_index": 0,
            },
            {
                "document_id": "doc-west",
                "content": "Western region office hours in Colombo are 09:00 to 17:00 on weekdays.",
                "category": "REGIONAL",
                "region": "WESTERN",
                "filename": "west_hours.xlsx",
                "source_page": None,
                "source_row": 2,
                "sheet_name": "Western",
                "status": "APPROVED",
                "chunk_index": 0,
            },
            {
                "document_id": "doc-secret",
                "content": "Confidential internal escalation contact is listed only for Super Users.",
                "category": "CONFIDENTIAL_INTERNAL",
                "region": None,
                "filename": "internal_escalation.csv",
                "source_page": None,
                "source_row": 2,
                "sheet_name": None,
                "status": "APPROVED",
                "chunk_index": 0,
            },
            {
                "document_id": "doc-pending",
                "content": "Pending leave policy draft must not appear in search.",
                "category": "GENERAL",
                "region": None,
                "filename": "draft.pdf",
                "source_page": 1,
                "status": "PENDING",
                "chunk_index": 0,
            },
        ]
    )


async def _search(client, token: str, query: str):
    return await client.post(
        "/retrieval/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query},
    )


@pytest.mark.asyncio
async def test_unauthenticated_search_is_rejected(client):
    response = await client.post("/retrieval/search", json={"query": "leave"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_normal_user_retrieves_general_only(client):
    await _seed_chunks()
    await _insert_user(email="normal@example.com", password="Password123", role=Role.NORMAL)
    token = await _login(client, "normal@example.com", "Password123")

    leave = await _search(client, token, "annual leave policy")
    assert leave.status_code == 200
    body = leave.json()
    assert body["insufficient_evidence"] is False
    assert all(match["category"] == "GENERAL" for match in body["matches"])
    assert any("leave" in match["content"].lower() for match in body["matches"])

    south = await _search(client, token, "Galle office hours")
    assert south.status_code == 200
    assert south.json()["insufficient_evidence"] is True
    assert south.json()["matches"] == []

    secret = await _search(client, token, "escalation contact Super")
    assert secret.json()["insufficient_evidence"] is True


@pytest.mark.asyncio
async def test_regional_southern_cannot_see_western_or_confidential(client):
    await _seed_chunks()
    await _insert_user(email="south@example.com", password="Password123", role=Role.REGIONAL, region="SOUTHERN")
    token = await _login(client, "south@example.com", "Password123")

    south = await _search(client, token, "Galle office hours")
    assert south.status_code == 200
    filenames = {match["filename"] for match in south.json()["matches"]}
    assert "south_hours.xlsx" in filenames
    assert "west_hours.xlsx" not in filenames

    west = await _search(client, token, "Colombo office hours Western")
    assert west.json()["insufficient_evidence"] is True or all(
        match["region"] != "WESTERN" for match in west.json()["matches"]
    )

    secret = await _search(client, token, "Confidential internal escalation")
    assert secret.json()["insufficient_evidence"] is True


@pytest.mark.asyncio
async def test_super_user_can_retrieve_confidential(client):
    await _seed_chunks()
    await _insert_user(email="super@example.com", password="Password123", role=Role.SUPER)
    token = await _login(client, "super@example.com", "Password123")

    secret = await _search(client, token, "Confidential internal escalation")
    assert secret.status_code == 200
    assert secret.json()["insufficient_evidence"] is False
    assert any(match["category"] == "CONFIDENTIAL_INTERNAL" for match in secret.json()["matches"])

    west = await _search(client, token, "Colombo Western office hours")
    assert any(match["region"] == "WESTERN" for match in west.json()["matches"])


@pytest.mark.asyncio
async def test_pending_chunks_never_returned(client):
    await _seed_chunks()
    await _insert_user(email="super@example.com", password="Password123", role=Role.SUPER)
    token = await _login(client, "super@example.com", "Password123")
    response = await _search(client, token, "Pending leave policy draft")
    filenames = {match["filename"] for match in response.json()["matches"]}
    assert "draft.pdf" not in filenames


@pytest.mark.asyncio
async def test_admin_retrieval_is_empty_until_slt_defines_chat_access(client):
    await _seed_chunks()
    await _insert_user(email="admin1@example.com", password="AdminPass123", role=Role.ADMIN)
    token = await _login(client, "admin1@example.com", "AdminPass123")
    response = await _search(client, token, "annual leave policy")
    assert response.status_code == 200
    assert response.json()["allowed_categories"] == []
    assert response.json()["insufficient_evidence"] is True
    assert response.json()["matches"] == []
