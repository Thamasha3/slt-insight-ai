"""CSV extraction with Pandas. Each row stays a labeled record."""

from pathlib import Path

import pandas as pd

from app.services.ingestion.errors import IngestionError
from app.services.ingestion.tabular import records_from_frame


def extract_csv_chunks(path: Path, *, filename: str, category: str, region: str | None) -> tuple[int | None, list[dict]]:
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    except UnicodeDecodeError:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="latin-1")
    except Exception as exc:
        raise IngestionError(f"Could not read CSV: {exc}") from exc

    if frame.empty:
        raise IngestionError("The CSV has no data rows.")

    records = records_from_frame(
        frame,
        filename=filename,
        category=category,
        region=region,
        sheet_name=None,
        start_index=0,
    )
    if not records:
        raise IngestionError("The CSV had no usable values after cleaning.")
    return None, records
