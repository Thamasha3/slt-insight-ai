"""
Chat orchestration: retrieve authorized chunks, then optionally call Gemini.

Unauthorized or PENDING text is never placed in the Gemini prompt.
"""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.auth.rbac import CurrentUser, chunk_is_visible_to, region_filter_for
from app.database.connection import chat_messages_collection, chat_sessions_collection
from app.models.audit import AuditAction
from app.models.chat import new_chat_message, new_chat_session, session_title_from_query
from app.models.document import DocumentStatus
from app.services.rag.citations import filter_authorized_to_cited, prose_without_trailing_bibliography
from app.services.rag.conversation import (
    NO_EVIDENCE_REPLY,
    compose_search_query,
    is_small_talk,
    small_talk_reply,
)
from app.services.rag.gemini import (
    INSUFFICIENT_EVIDENCE,
    GeminiCallError,
    GeminiNotConfiguredError,
    generate_answer,
)
from app.services.rag.retrieve import allowed_category_list, search_visible_chunks
from app.utils.audit import write_audit_log


def _citation_from_match(match: dict, citation_index: int) -> dict:
    return {
        "document_id": match.get("document_id") or "",
        "filename": match.get("filename") or "",
        "category": match.get("category") or "",
        "region": match.get("region"),
        "source_page": match.get("source_page"),
        "source_row": match.get("source_row"),
        "sheet_name": match.get("sheet_name"),
        "content": match.get("content") or "",
        "score": match.get("score") or 0.0,
        "citation_index": citation_index,
    }


async def _get_owned_session(user: CurrentUser, session_id: str) -> dict:
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session id")
    session = await chat_sessions_collection().find_one({"_id": ObjectId(session_id)})
    if session is None or session.get("user_id") != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return session


async def _session_history(user_id: str, session_id: str) -> list[dict]:
    cursor = (
        chat_messages_collection()
        .find({"session_id": session_id, "user_id": user_id})
        .sort("created_at", 1)
        .limit(20)
    )
    history = []
    async for document in cursor:
        history.append(
            {
                "role": document.get("role") or "user",
                "content": document.get("content") or "",
            }
        )
    return history


def _normalize_model_answer(text: str) -> tuple[str, bool]:
    cleaned = (text or "").strip()
    if not cleaned or cleaned.lower() == INSUFFICIENT_EVIDENCE.lower():
        return NO_EVIDENCE_REPLY, True
    return cleaned, False


async def answer_employee_question(
    user: CurrentUser,
    query: str,
    *,
    session_id: str | None,
    limit: int = 8,
) -> dict:
    history: list[dict] = []
    if session_id:
        await _get_owned_session(user, session_id)
        history = await _session_history(user.id, session_id)

    if is_small_talk(query):
        answer = small_talk_reply(user, query)
        return await _persist_turn(
            user,
            query=query,
            session_id=session_id,
            answer=answer,
            authorized=[],
            gemini_called=False,
            insufficient=False,
        )

    prior_user = [turn["content"] for turn in history if turn.get("role") == "user"]
    search_query = compose_search_query(query, prior_user)
    matches = await search_visible_chunks(user, search_query, limit=limit)
    authorized = []
    for match in matches:
        gate_chunk = {
            **match,
            "status": DocumentStatus.APPROVED.value,
        }
        if chunk_is_visible_to(user, gate_chunk):
            authorized.append(match)

    insufficient = len(authorized) == 0
    gemini_called = False
    if insufficient:
        answer = NO_EVIDENCE_REPLY
    else:
        try:
            raw = await run_in_threadpool(
                generate_answer,
                query=query,
                chunks=authorized,
                history=history,
            )
            gemini_called = True
            answer, model_insufficient = _normalize_model_answer(
                prose_without_trailing_bibliography(raw)
            )
            insufficient = model_insufficient
        except GeminiNotConfiguredError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except GeminiCallError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The language model could not be reached. No unauthorized text was sent.",
            ) from exc

    return await _persist_turn(
        user,
        query=query,
        session_id=session_id,
        answer=answer,
        authorized=authorized,
        gemini_called=gemini_called,
        insufficient=insufficient,
    )


async def _persist_turn(
    user: CurrentUser,
    *,
    query: str,
    session_id: str | None,
    answer: str,
    authorized: list[dict],
    gemini_called: bool,
    insufficient: bool,
) -> dict:
    if session_id:
        session = await _get_owned_session(user, session_id)
        sid = str(session["_id"])
    else:
        record = new_chat_session(user_id=user.id, title=session_title_from_query(query))
        inserted = await chat_sessions_collection().insert_one(record)
        sid = str(inserted.inserted_id)

    citations = [
        _citation_from_match(item, citation_index)
        for citation_index, item in filter_authorized_to_cited(authorized, answer)
    ]
    await chat_messages_collection().insert_one(
        new_chat_message(session_id=sid, user_id=user.id, role="user", content=query)
    )
    await chat_messages_collection().insert_one(
        new_chat_message(
            session_id=sid,
            user_id=user.id,
            role="assistant",
            content=answer,
            citations=citations,
            gemini_called=gemini_called,
            insufficient_evidence=insufficient,
        )
    )

    await chat_sessions_collection().update_one(
        {"_id": ObjectId(sid)},
        {"$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    await write_audit_log(
        user_id=user.id,
        action=AuditAction.CHAT_QUERY.value,
        resource=f"chat/{sid}",
        status_="EMPTY" if insufficient else ("GEMINI" if gemini_called else "SUCCESS"),
    )
    return {
        "session_id": sid,
        "query": query,
        "answer": answer,
        "insufficient_evidence": insufficient,
        "gemini_called": gemini_called,
        "allowed_categories": allowed_category_list(user),
        "region_filter": region_filter_for(user),
        "citations": citations,
    }
