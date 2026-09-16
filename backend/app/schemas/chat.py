from pydantic import BaseModel, ConfigDict, Field

from app.schemas.retrieval import RetrievedChunkOut


class ChatAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    limit: int = Field(default=8, ge=1, le=20)


class ChatAskResponse(BaseModel):
    session_id: str
    query: str
    answer: str
    insufficient_evidence: bool
    gemini_called: bool
    allowed_categories: list[str]
    region_filter: str | None
    citations: list[RetrievedChunkOut]


class ChatSessionOut(BaseModel):
    id: str
    title: str
    created_at: object | None = None
    updated_at: object | None = None


class ChatMessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: list[RetrievedChunkOut]
    gemini_called: bool
    insufficient_evidence: bool
    created_at: object | None = None
