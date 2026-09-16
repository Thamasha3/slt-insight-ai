"""Employee chat. Gemini is called only after RBAC retrieval."""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.rbac import CurrentUser, get_current_user
from app.database.connection import chat_messages_collection, chat_sessions_collection
from app.schemas.chat import ChatAskRequest, ChatAskResponse, ChatMessageOut, ChatSessionOut
from app.schemas.retrieval import RetrievedChunkOut
from app.services.rag.chat import answer_employee_question

router = APIRouter(prefix="/chat", tags=["chat"])


def _session_out(document: dict) -> ChatSessionOut:
    return ChatSessionOut(
        id=str(document["_id"]),
        title=document.get("title") or "Chat",
        created_at=document.get("created_at"),
        updated_at=document.get("updated_at"),
    )


def _message_out(document: dict) -> ChatMessageOut:
    citations = []
    for item in document.get("citations") or []:
        citations.append(RetrievedChunkOut(**item) if not isinstance(item, RetrievedChunkOut) else item)
    return ChatMessageOut(
        id=str(document["_id"]),
        session_id=document["session_id"],
        role=document["role"],
        content=document["content"],
        citations=citations,
        gemini_called=bool(document.get("gemini_called")),
        insufficient_evidence=bool(document.get("insufficient_evidence")),
        created_at=document.get("created_at"),
    )


@router.post("", response_model=ChatAskResponse)
async def ask_chat(payload: ChatAskRequest, user: CurrentUser = Depends(get_current_user)):
    result = await answer_employee_question(
        user,
        payload.query.strip(),
        session_id=payload.session_id,
        limit=payload.limit,
    )
    return ChatAskResponse(
        session_id=result["session_id"],
        query=result["query"],
        answer=result["answer"],
        insufficient_evidence=result["insufficient_evidence"],
        gemini_called=result["gemini_called"],
        allowed_categories=result["allowed_categories"],
        region_filter=result["region_filter"],
        citations=[RetrievedChunkOut(**item) for item in result["citations"]],
    )


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(user: CurrentUser = Depends(get_current_user)):
    cursor = chat_sessions_collection().find({"user_id": user.id}).sort("updated_at", -1).limit(50)
    return [_session_out(document) async for document in cursor]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def list_messages(session_id: str, user: CurrentUser = Depends(get_current_user)):
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session id")
    session = await chat_sessions_collection().find_one({"_id": ObjectId(session_id), "user_id": user.id})
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    cursor = chat_messages_collection().find({"session_id": session_id, "user_id": user.id}).sort("created_at", 1)
    return [_message_out(document) async for document in cursor]
