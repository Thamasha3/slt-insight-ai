"""Excel extraction. Each sheet is read as a table; row + sheet names are kept for citations."""

from pathlib import Path

import pandas as pd

from app.services.ingestion.errors import IngestionError
from app.services.ingestion.tabular import records_from_frame


def extract_excel_chunks(path: Path, *, filename: str, category: str, region: str | None) -> tuple[int | None, list[dict]]:
    try:
        workbook = pd.read_excel(path, sheet_name=None, dtype=str, engine="openpyxl")
    except Exception as exc:
        raise IngestionError(f"Could not read Excel workbook: {exc}") from exc

    if not workbook:
        raise IngestionError("The Excel file has no sheets.")

    records: list[dict] = []
    for sheet_name, frame in workbook.items():
        if frame is None or frame.empty:
            continue
        records.extend(
            records_from_frame(
                frame,
                filename=filename,
                category=category,
                region=region,
                sheet_name=str(sheet_name),
                start_index=len(records),
            )
        )

    if not records:
        raise IngestionError("The Excel workbook had no usable table rows after cleaning.")
    return None, records
