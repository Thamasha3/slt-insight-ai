from pydantic import BaseModel, ConfigDict, Field


class RetrievalSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=8, ge=1, le=20)


class RetrievedChunkOut(BaseModel):
    document_id: str
    filename: str
    category: str
    region: str | None
    source_page: int | None
    source_row: int | None
    sheet_name: str | None
    content: str
    score: float
    citation_index: int | None = None


class RetrievalSearchResponse(BaseModel):
    query: str
    allowed_categories: list[str]
    region_filter: str | None
    insufficient_evidence: bool
    matches: list[RetrievedChunkOut]
