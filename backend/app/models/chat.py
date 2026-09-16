"""Chat session and message record shapes."""

from datetime import datetime, timezone


def new_chat_session(*, user_id: str, title: str) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    }


def new_chat_message(
    *,
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    citations: list[dict] | None = None,
    gemini_called: bool = False,
    insufficient_evidence: bool = False,
) -> dict:
    return {
        "session_id": session_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "citations": citations or [],
        "gemini_called": gemini_called,
        "insufficient_evidence": insufficient_evidence,
        "created_at": datetime.now(timezone.utc),
    }


def session_title_from_query(query: str) -> str:
    cleaned = " ".join(query.strip().split())
    if len(cleaned) <= 80:
        return cleaned or "New chat"
    return cleaned[:77] + "..."
