"""Turn CSV/Excel rows into labeled records (not a blob of comma-separated text)."""

from __future__ import annotations

import math

import pandas as pd

from app.services.ingestion.chunking import chunk_text


MAX_TABLE_ROWS = 10_000


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and (math.isnan(value) or pd.isna(value)):
        return ""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>"}:
        return ""
    return text


def normalize_columns(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for index, raw in enumerate(columns):
        name = _cell_text(raw) or f"column_{index + 1}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        result.append(name if count == 0 else f"{name}_{count + 1}")
    return result


def row_to_text(
    columns: list[str],
    values,
    *,
    record_number: int,
    sheet_name: str | None,
) -> str:
    lines: list[str] = []
    if sheet_name:
        lines.append(f"Sheet: {sheet_name}")
    lines.append(f"Record: {record_number}")
    for column, value in zip(columns, values, strict=False):
        text = _cell_text(value)
        if not text:
            continue
        lines.append(f"{column}: {text}")
    return "\n".join(lines)


def records_from_frame(
    frame: pd.DataFrame,
    *,
    filename: str,
    category: str,
    region: str | None,
    sheet_name: str | None,
    start_index: int,
) -> list[dict]:
    if frame.empty:
        return []

    cleaned = frame.copy()
    cleaned.columns = normalize_columns([str(column) for column in cleaned.columns])
    cleaned = cleaned.dropna(how="all")

    records: list[dict] = []
    chunk_index = start_index
    row_count = 0
    for excel_row_number, row in cleaned.iterrows():
        row_count += 1
        if row_count > MAX_TABLE_ROWS:
            break
        record_number = int(excel_row_number) + 2 if isinstance(excel_row_number, (int, float)) else len(records) + 1
        content = row_to_text(
            list(cleaned.columns),
            row.tolist(),
            record_number=record_number,
            sheet_name=sheet_name,
        )
        pieces = chunk_text(content)
        if not pieces:
            continue
        source_row = int(excel_row_number) + 2 if isinstance(excel_row_number, (int, float)) else record_number
        for piece in pieces:
            records.append(
                {
                    "content": piece,
                    "category": category,
                    "region": region,
                    "filename": filename,
                    "source_page": None,
                    "source_row": source_row,
                    "sheet_name": sheet_name,
                    "section": None,
                    "chunk_index": chunk_index,
                }
            )
            chunk_index += 1
    return records
