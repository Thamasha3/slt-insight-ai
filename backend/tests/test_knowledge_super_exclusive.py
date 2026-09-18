from io import BytesIO

import fitz
import pytest

from app.auth.security import hash_password
from app.database.connection import users_collection
from app.models.user import Role, UserStatus, new_user_document


def _pdf_bytes(text: str = "Sample leave policy: employees may request annual leave through HR.") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    buffer = BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


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


@pytest.mark.asyncio
async def test_admin_cannot_approve_update_or_delete_knowledge(client):
    await _insert_user(email="admin1@example.com", password="AdminPass123", role=Role.ADMIN)
    await _insert_user(email="super@example.com", password="Password123", role=Role.SUPER)
    admin_token = await _login(client, "admin1@example.com", "AdminPass123")
    super_token = await _login(client, "super@example.com", "Password123")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    super_headers = {"Authorization": f"Bearer {super_token}"}

    upload = await client.post(
        "/admin/knowledge/upload",
        headers=admin_headers,
        files={"file": ("hr_policy.pdf", _pdf_bytes(), "application/pdf")},
        data={"category": "GENERAL", "description": "admin upload"},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    approve = await client.post(f"/admin/knowledge/{document_id}/approve", headers=admin_headers)
    reject = await client.post(f"/admin/knowledge/{document_id}/reject", headers=admin_headers)
    update = await client.put(
        f"/admin/knowledge/{document_id}",
        headers=admin_headers,
        json={"category": "CONFIDENTIAL_INTERNAL"},
    )
    deleted = await client.delete(f"/admin/knowledge/{document_id}", headers=admin_headers)
    assert approve.status_code == 403
    assert reject.status_code == 403
    assert update.status_code == 403
    assert deleted.status_code == 403

    super_update = await client.put(
        f"/admin/knowledge/{document_id}",
        headers=super_headers,
        json={"description": "reclassified by Super User", "category": "CONFIDENTIAL_INTERNAL"},
    )
    assert super_update.status_code == 200
    assert super_update.json()["category"] == "CONFIDENTIAL_INTERNAL"

    super_approve = await client.post(f"/admin/knowledge/{document_id}/approve", headers=super_headers)
    assert super_approve.status_code == 200
    assert super_approve.json()["status"] == "APPROVED"
