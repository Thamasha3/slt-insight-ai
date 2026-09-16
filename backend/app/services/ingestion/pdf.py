"""
PDF extraction with PyMuPDF.

Scanned (image-only) PDFs produce no text. OCR is intentionally not enabled yet.
"""

from pathlib import Path

import fitz

from app.services.ingestion.chunking import chunk_text
from app.services.ingestion.text_clean import clean_extracted_text


def extract_pdf_chunks(path: Path, *, filename: str, category: str, region: str | None) -> tuple[int, list[dict]]:
    document = fitz.open(path)
    try:
        page_count = document.page_count
        records: list[dict] = []
        chunk_index = 0
        for page_number in range(page_count):
            page = document.load_page(page_number)
            raw = page.get_text("text") or ""
            cleaned = clean_extracted_text(raw)
            for piece in chunk_text(cleaned):
                records.append(
                    {
                        "content": piece,
                        "category": category,
                        "region": region,
                        "filename": filename,
                        "source_page": page_number + 1,
                        "source_row": None,
                        "sheet_name": None,
                        "section": None,
                        "chunk_index": chunk_index,
                    }
                )
                chunk_index += 1
        return page_count, records
    finally:
        document.close()
