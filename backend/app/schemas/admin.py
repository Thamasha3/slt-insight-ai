from pydantic import BaseModel


class AdminStatsOut(BaseModel):
    users_total: int
    users_pending: int
    users_active: int
    documents_total: int
    documents_pending: int
    documents_approved: int
    documents_rejected: int
    documents_failed: int
    chunks_approved: int
    knowledge_by_category: dict[str, int]
