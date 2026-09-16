from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus, KnowledgeCategory
from app.models.user import Region


class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: str
    category: str
    region: str | None
    description: str
    status: str
    uploaded_by: str
    page_count: int | None
    chunk_count: int
    error_message: str | None
    created_at: datetime | None = None


class DocumentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, max_length=2000)
    category: KnowledgeCategory | None = None
    region: Region | None = None


class ChunkOut(BaseModel):
    id: str
    document_id: str
    content: str
    category: str
    region: str | None
    filename: str
    source_page: int | None
    source_row: int | None = None
    sheet_name: str | None = None
    chunk_index: int
    status: str
