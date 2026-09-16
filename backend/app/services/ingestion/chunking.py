"""Split long page/sheet text into overlapping chunks for later retrieval."""

from app.services.ingestion.text_clean import clean_extracted_text

MAX_CHUNK_CHARS = 1200
OVERLAP_CHARS = 150


def chunk_text(text: str) -> list[str]:
    cleaned = clean_extracted_text(text)
    if not cleaned:
        return []
    if len(cleaned) <= MAX_CHUNK_CHARS:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + MAX_CHUNK_CHARS, length)
        piece = cleaned[start:end]
        if end < length:
            break_at = max(piece.rfind("\n"), piece.rfind(". "), piece.rfind(" "))
            if break_at >= MAX_CHUNK_CHARS // 3:
                end = start + break_at + 1
                piece = cleaned[start:end].strip()
        piece = piece.strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(0, end - OVERLAP_CHARS)
    return chunks
