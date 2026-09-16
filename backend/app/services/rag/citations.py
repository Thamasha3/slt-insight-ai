"""Keep chat source lists aligned with [n] markers in the model answer."""

from __future__ import annotations

import re

# [1], [1, 2], and fullwidth 【1】 as used in some Gemini outputs.
_CITATION_REF = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]|【(\d+)】")
_TRAILING_CITE_LINE = re.compile(r"^\[\d+\](\s+.+)?$")
_TRAILING_HEADING = re.compile(r"^(sources?|references|citations)\s*:?\s*$", re.IGNORECASE)


def _prose_without_trailing_bibliography(answer: str) -> str:
    """Drop a trailing source dump so unused [2]/[3] lines are not treated as citations."""
    lines = (answer or "").splitlines()
    while lines:
        stripped = lines[-1].strip()
        if not stripped:
            lines.pop()
            continue
        if _TRAILING_CITE_LINE.match(stripped) or _TRAILING_HEADING.match(stripped):
            lines.pop()
            continue
        break
    return "\n".join(lines)


def prose_without_trailing_bibliography(answer: str) -> str:
    return _prose_without_trailing_bibliography(answer)


def cited_snippet_indexes(answer: str) -> list[int]:
    """Return unique 1-based snippet indexes in the order they first appear in the answer prose."""
    seen: list[int] = []
    for match in _CITATION_REF.finditer(prose_without_trailing_bibliography(answer)):
        packed = match.group(1) or match.group(2) or ""
        for part in packed.split(","):
            number = int(part.strip())
            if number not in seen:
                seen.append(number)
    return seen


def filter_authorized_to_cited(authorized: list[dict], answer: str) -> list[tuple[int, dict]]:
    """
    Map answer citations like [1] onto the same numbered evidence list sent to Gemini.

    Out-of-range markers are ignored. Duplicates keep the first occurrence only.
    Unused retrieved chunks are not returned.
    """
    selected: list[tuple[int, dict]] = []
    for number in cited_snippet_indexes(answer):
        if 1 <= number <= len(authorized):
            selected.append((number, authorized[number - 1]))
    return selected
