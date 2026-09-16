"""Document / knowledge-source enums and record shapes."""

from datetime import datetime, timezone
from enum import StrEnum


class KnowledgeCategory(StrEnum):
    GENERAL = "GENERAL"
    REGIONAL = "REGIONAL"
    CONFIDENTIAL_INTERNAL = "CONFIDENTIAL_INTERNAL"


class DocumentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


ALLOWED_EXTENSIONS = {"pdf", "docx", "csv", "xlsx", "xls"}


def new_document_record(
    *,
    filename: str,
    stored_path: str,
    file_type: str,
    category: str,
    region: str | None,
    description: str,
    uploaded_by: str,
    status: DocumentStatus,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "filename": filename,
        "stored_path": stored_path,
        "file_type": file_type,
        "category": category,
        "region": region,
        "description": description,
        "status": status.value,
        "uploaded_by": uploaded_by,
        "page_count": None,
        "chunk_count": 0,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }
