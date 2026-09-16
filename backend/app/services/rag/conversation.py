"""Chatbot-style intent helpers. Permissions still live in rbac.py."""

from __future__ import annotations

import re

from app.auth.rbac import CurrentUser
from app.services.rag.retrieve import allowed_category_list, tokenize

_PUNCT = re.compile(r"[^\w\s']+")
_SPACE = re.compile(r"\s+")

_SMALL_TALK = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "yo",
    "howdy",
    "good morning",
    "good afternoon",
    "good evening",
    "thanks",
    "thank you",
    "thank you so much",
    "thx",
    "ok",
    "okay",
    "bye",
    "goodbye",
    "see you",
    "who are you",
    "who are you?",
    "what are you",
    "what can you do",
    "what can you help with",
    "help",
    "help me",
    "how does this work",
    "how do you work",
}

_SMALL_TALK_PREFIX = re.compile(
    r"^(hi|hello|hey|good\s+(morning|afternoon|evening)|thanks|thank you|"
    r"who are you|what( are|'?re) you|what can you( do| help with)?|help|"
    r"how does this work)\b",
    re.IGNORECASE,
)

_FOLLOWUP = {
    "it",
    "that",
    "this",
    "those",
    "them",
    "there",
    "more",
    "also",
    "same",
    "again",
}

NO_EVIDENCE_REPLY = (
    "I don't have approved information I can share with you for that question. "
    "Try asking about a topic covered in your knowledge base, or rephrase using "
    "words from those documents."
)


def normalize_utterance(text: str) -> str:
    cleaned = _PUNCT.sub(" ", (text or "").strip().lower())
    return _SPACE.sub(" ", cleaned).strip()


def is_small_talk(query: str) -> bool:
    cleaned = normalize_utterance(query)
    if not cleaned:
        return False
    if cleaned in _SMALL_TALK:
        return True
    if len(cleaned.split()) <= 8 and _SMALL_TALK_PREFIX.match(cleaned):
        return True
    return False


def small_talk_reply(user: CurrentUser, query: str) -> str:
    first = (user.name or "there").split()[0]
    cleaned = normalize_utterance(query)
    categories = allowed_category_list(user)

    if cleaned in {"thanks", "thank you", "thank you so much", "thx"}:
        return f"You're welcome, {first}. Ask another question whenever you need to."
    if cleaned in {"bye", "goodbye", "see you"}:
        return f"Goodbye, {first}. Sign in again whenever you need SLT information."
    if cleaned in {"ok", "okay"}:
        return "Okay. What would you like to know?"

    if not categories:
        return (
            f"Hello {first}. I'm SLT insight.ai, the internal chatbot. "
            "Admin accounts manage users and knowledge sources. "
            "Employee knowledge answers are limited to Super, Regional, and Normal users."
        )

    labels = {
        "GENERAL": "general",
        "REGIONAL": "regional",
        "CONFIDENTIAL_INTERNAL": "confidential/internal",
    }
    access = ", ".join(labels.get(item, item.lower()) for item in categories)
    region = f" for {user.region}" if user.region else ""
    return (
        f"Hello {first}. I'm SLT insight.ai, your internal chatbot. "
        f"I can answer from approved {access} information{region}. "
        "Ask a question in plain language and I'll look it up for you."
    )


def compose_search_query(query: str, prior_user_messages: list[str]) -> str:
    """Blend follow-up questions with earlier turns so keyword search still hits."""
    current = (query or "").strip()
    if not prior_user_messages:
        return current
    tokens = set(tokenize(current))
    followup = len(tokens) <= 5 or bool(tokens & _FOLLOWUP)
    if not followup:
        return current
    recent = [item.strip() for item in prior_user_messages[-2:] if item and item.strip()]
    return " ".join(recent + [current])
