"""
Permission-aware retrieval (Phase 7, without Gemini).

This is the filing-cabinet search:

1. Load the logged-in user's role and region from MongoDB (already done by auth).
2. Keep only APPROVED chunks that person may see.
3. Rank those chunks against the question with keyword overlap.

Gemini is not called here. Embeddings / vector search can replace the
keyword ranker later without changing the permission filter.
"""

from __future__ import annotations

import re

from app.auth.rbac import CurrentUser, allowed_categories_for, chunk_is_visible_to, retrieval_mongo_filter
from app.database.connection import document_chunks_collection

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
}


def tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN.findall(text.lower()) if token not in _STOP and len(token) > 1]


def _variants(token: str) -> set[str]:
    variants = {token}
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            variants.add(token[: -len(suffix)])
    return variants


def score_chunk(query: str, content: str) -> float:
    haystack = (content or "").lower()
    if not haystack:
        return 0.0
    tokens = tokenize(query)
    if not tokens:
        needle = query.strip().lower()
        return 1.0 if needle and needle in haystack else 0.0
    unique_hits = 0
    occurrences = 0
    for token in set(tokens):
        matched = any(variant in haystack for variant in _variants(token) if len(variant) > 1)
        if matched:
            unique_hits += 1
            occurrences += max(haystack.count(item) for item in _variants(token) if item)
    phrase = " ".join(tokens)
    phrase_bonus = 6.0 if len(tokens) >= 2 and phrase and phrase in haystack else 0.0
    bigram_bonus = 0.0
    for left, right in zip(tokens, tokens[1:]):
        if f"{left} {right}" in haystack:
            bigram_bonus += 2.0
    return float(unique_hits * 2 + min(occurrences, 20) + phrase_bonus + bigram_bonus)


async def search_visible_chunks(user: CurrentUser, query: str, *, limit: int = 8) -> list[dict]:
    mongo_filter = retrieval_mongo_filter(user)
    if mongo_filter is None:
        return []

    cursor = document_chunks_collection().find(mongo_filter)
    scored: list[tuple[float, dict]] = []
    async for chunk in cursor:
        if not chunk_is_visible_to(user, chunk):
            continue
        searchable = f"{chunk.get('filename') or ''} {chunk.get('content') or ''}"
        points = score_chunk(query, searchable)
        if points <= 0:
            continue
        scored.append((points, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    if scored:
        top_score = scored[0][0]
        floor = max(2.0, top_score * 0.4)
        scored = [item for item in scored if item[0] >= floor]
    matches = []
    for points, chunk in scored[:limit]:
        matches.append(
            {
                "document_id": chunk.get("document_id") or "",
                "filename": chunk.get("filename") or "",
                "category": chunk.get("category") or "",
                "region": chunk.get("region"),
                "source_page": chunk.get("source_page"),
                "source_row": chunk.get("source_row"),
                "sheet_name": chunk.get("sheet_name"),
                "content": chunk.get("content") or "",
                "score": points,
            }
        )
    return matches


def allowed_category_list(user: CurrentUser) -> list[str]:
    return sorted(allowed_categories_for(user))
