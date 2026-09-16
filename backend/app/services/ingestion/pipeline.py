"""Run file-type-specific extraction for PDF, Word, CSV, and Excel."""

from pathlib import Path

from app.services.ingestion.csv import extract_csv_chunks
from app.services.ingestion.docx import extract_docx_chunks
from app.services.ingestion.errors import IngestionError
from app.services.ingestion.excel import extract_excel_chunks
from app.services.ingestion.pdf import extract_pdf_chunks


def extract_chunks(
    *,
    path: Path,
    file_type: str,
    filename: str,
    category: str,
    region: str | None,
) -> tuple[int | None, list[dict]]:
    if file_type == "pdf":
        page_count, records = extract_pdf_chunks(path, filename=filename, category=category, region=region)
        if not records:
            raise IngestionError(
                "No extractable text was found. Scanned PDFs need OCR, which is not enabled yet. "
                "Use a text-based PDF for this phase."
            )
        return page_count, records

    if file_type == "csv":
        return extract_csv_chunks(path, filename=filename, category=category, region=region)

    if file_type == "xlsx":
        return extract_excel_chunks(path, filename=filename, category=category, region=region)

    if file_type == "docx":
        return extract_docx_chunks(path, filename=filename, category=category, region=region)

    if file_type == "xls":
        raise IngestionError("Legacy .xls is not supported. Save the workbook as .xlsx and upload again.")

    raise IngestionError(f"Unsupported file type: {file_type}")
