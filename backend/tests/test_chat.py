"""Chat + Gemini gate tests. The mock never talks to Vertex."""

import pytest

from app.auth.security import hash_password
from app.database.connection import document_chunks_collection, users_collection
from app.models.user import Role, UserStatus, new_user_document
from app.services.rag import chat as chat_service
from app.services.rag.conversation import NO_EVIDENCE_REPLY


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
        ]
    )


@pytest.fixture
def capture_gemini(monkeypatch):
    calls = []

    def fake_generate(*, query: str, chunks: list[dict], history=None) -> str:
        calls.append({"query": query, "chunks": chunks, "history": history or []})
        return "Employees request annual leave through HR. [1]"

    monkeypatch.setattr(chat_service, "generate_answer", fake_generate)
    return calls


@pytest.mark.asyncio
async def test_chat_without_evidence_does_not_call_gemini(client, capture_gemini):
    await _insert_user(email="normal@example.com", password="Password123", role=Role.NORMAL)
    token = await _login(client, "normal@example.com", "Password123")
    response = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "escalation contact Super Users"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["insufficient_evidence"] is True
    assert body["gemini_called"] is False
    assert body["answer"] == NO_EVIDENCE_REPLY
    assert capture_gemini == []


@pytest.mark.asyncio
async def test_normal_chat_sends_only_general_chunks(client, capture_gemini):
    await _seed_chunks()
    await _insert_user(email="normal@example.com", password="Password123", role=Role.NORMAL)
    token = await _login(client, "normal@example.com", "Password123")
    response = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "annual leave policy"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gemini_called"] is True
    assert body["insufficient_evidence"] is False
    assert len(capture_gemini) == 1
    sent = capture_gemini[0]["chunks"]
    assert sent
    assert all(chunk["category"] == "GENERAL" for chunk in sent)
    joined = " ".join(chunk["content"] for chunk in sent)
    assert "Confidential" not in joined
    assert "Galle" not in joined


@pytest.mark.asyncio
async def test_super_chat_may_include_confidential(client, capture_gemini):
    await _seed_chunks()
    await _insert_user(email="super@example.com", password="Password123", role=Role.SUPER)
    token = await _login(client, "super@example.com", "Password123")
    response = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Confidential internal escalation"},
    )
    assert response.status_code == 200
    assert response.json()["gemini_called"] is True
    categories = {chunk["category"] for chunk in capture_gemini[0]["chunks"]}
    assert "CONFIDENTIAL_INTERNAL" in categories


@pytest.mark.asyncio
async def test_admin_chat_never_calls_gemini(client, capture_gemini):
    await _seed_chunks()
    await _insert_user(email="admin1@example.com", password="AdminPass123", role=Role.ADMIN)
    token = await _login(client, "admin1@example.com", "AdminPass123")
    response = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "annual leave policy"},
    )
    assert response.status_code == 200
    assert response.json()["gemini_called"] is False
    assert response.json()["insufficient_evidence"] is True
    assert capture_gemini == []


@pytest.mark.asyncio
async def test_user_cannot_read_another_users_session(client, capture_gemini):
    await _seed_chunks()
    await _insert_user(email="a@example.com", password="Password123", role=Role.NORMAL)
    await _insert_user(email="b@example.com", password="Password123", role=Role.NORMAL)
    token_a = await _login(client, "a@example.com", "Password123")
    token_b = await _login(client, "b@example.com", "Password123")
    created = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"query": "annual leave policy"},
    )
    session_id = created.json()["session_id"]
    blocked = await client.get(
        f"/chat/sessions/{session_id}/messages",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert blocked.status_code == 404


@pytest.mark.asyncio
async def test_greeting_does_not_call_gemini(client, capture_gemini):
    await _insert_user(email="normal@example.com", password="Password123", role=Role.NORMAL)
    token = await _login(client, "normal@example.com", "Password123")
    response = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "hello"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["gemini_called"] is False
    assert body["insufficient_evidence"] is False
    assert "insight.ai" in body["answer"]
    assert capture_gemini == []


@pytest.mark.asyncio
async def test_follow_up_uses_previous_question_for_retrieval(client, capture_gemini):
    await _seed_chunks()
    await _insert_user(email="normal@example.com", password="Password123", role=Role.NORMAL)
    token = await _login(client, "normal@example.com", "Password123")
    first = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "annual leave policy"},
    )
    session_id = first.json()["session_id"]
    second = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "tell me more about that", "session_id": session_id},
    )
    assert second.status_code == 200
    assert second.json()["gemini_called"] is True
    assert second.json()["insufficient_evidence"] is False
    assert len(capture_gemini) == 2
    assert capture_gemini[1]["history"]


@pytest.mark.asyncio
async def test_chat_returns_only_sources_cited_in_the_answer(client, monkeypatch):
    await document_chunks_collection().insert_many(
        [
            {
                "document_id": "doc-matara",
                "content": "Matara branch operates Monday to Friday from 09:00 to 16:30.",
                "category": "GENERAL",
                "region": None,
                "filename": "Matara Branch Information.pdf",
                "source_page": 1,
                "source_row": None,
                "sheet_name": None,
                "status": "APPROVED",
                "chunk_index": 0,
            },
            {
                "document_id": "doc-revenue",
                "content": "Matara branch revenue sample figures for the quarterly report.",
                "category": "GENERAL",
                "region": None,
                "filename": "Revenue Report.csv",
                "source_page": None,
                "source_row": 4,
                "sheet_name": None,
                "status": "APPROVED",
                "chunk_index": 0,
            },
            {
                "document_id": "doc-complaints",
                "content": "Matara branch complaint handling sample notes.",
                "category": "GENERAL",
                "region": None,
                "filename": "Complaints.xlsx",
                "source_page": None,
                "source_row": 2,
                "sheet_name": "Sheet1",
                "status": "APPROVED",
                "chunk_index": 0,
            },
        ]
    )
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda **_: "The Matara branch operates from Monday to Friday, from 9:00 AM to 4:30 PM [1].",
    )
    await _insert_user(email="normal@example.com", password="Password123", role=Role.NORMAL)
    token = await _login(client, "normal@example.com", "Password123")
    response = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Matara branch operating hours"},
    )
    assert response.status_code == 200
    citations = response.json()["citations"]
    assert [item["filename"] for item in citations] == ["Matara Branch Information.pdf"]
    assert citations[0]["citation_index"] == 1


@pytest.mark.asyncio
async def test_chat_ignores_trailing_unused_bibliography(client, monkeypatch):
    await document_chunks_collection().insert_many(
        [
            {
                "document_id": "doc-matara",
                "content": "Matara branch operates Monday to Friday from 09:00 to 16:30.",
                "category": "GENERAL",
                "region": None,
                "filename": "Matara Branch Information.pdf",
                "source_page": 1,
                "source_row": None,
                "sheet_name": None,
                "status": "APPROVED",
                "chunk_index": 0,
            },
            {
                "document_id": "doc-revenue",
                "content": "Matara branch revenue sample figures for the quarterly report.",
                "category": "GENERAL",
                "region": None,
                "filename": "Revenue Report.csv",
                "source_page": None,
                "source_row": 4,
                "sheet_name": None,
                "status": "APPROVED",
                "chunk_index": 0,
            },
        ]
    )
    monkeypatch.setattr(
        chat_service,
        "generate_answer",
        lambda **_: (
            "The Matara branch operates from Monday to Friday, from 9:00 AM to 4:30 PM [1].\n\n"
            "Sources:\n"
            "[1] Matara Branch Information.pdf\n"
            "[2] Revenue Report.csv"
        ),
    )
    await _insert_user(email="normal@example.com", password="Password123", role=Role.NORMAL)
    token = await _login(client, "normal@example.com", "Password123")
    response = await client.post(
        "/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Matara branch operating hours"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "Revenue Report.csv" not in body["answer"]
    assert [item["filename"] for item in body["citations"]] == ["Matara Branch Information.pdf"]
