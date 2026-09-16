"""Employee retrieval API. Permissions are enforced here, not in React."""

from fastapi import APIRouter, Depends

from app.auth.rbac import CurrentUser, get_current_user, region_filter_for
from app.models.audit import AuditAction
from app.schemas.retrieval import RetrievedChunkOut, RetrievalSearchRequest, RetrievalSearchResponse
from app.services.rag.retrieve import allowed_category_list, search_visible_chunks
from app.utils.audit import write_audit_log

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalSearchResponse)
async def search_knowledge(
    payload: RetrievalSearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    matches = await search_visible_chunks(user, payload.query.strip(), limit=payload.limit)
    await write_audit_log(
        user_id=user.id,
        action=AuditAction.DATA_ACCESS.value,
        resource="retrieval/search",
        status_="SUCCESS" if matches else "EMPTY",
    )
    return RetrievalSearchResponse(
        query=payload.query.strip(),
        allowed_categories=allowed_category_list(user),
        region_filter=region_filter_for(user),
        insufficient_evidence=len(matches) == 0,
        matches=[RetrievedChunkOut(**item) for item in matches],
    )
