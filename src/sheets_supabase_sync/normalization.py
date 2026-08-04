from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from typing import Any


def normalize_column(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "_", value.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unnamed_column"


def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.strip().split())
    return value


def normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {normalize_column(str(key)): normalize_value(value) for key, value in row.items()}


def infer_type(values: list[Any]) -> str:
    non_empty = [value for value in values if value not in (None, "")]
    if not non_empty:
        return "text"
    if all(isinstance(value, bool) for value in non_empty):
        return "boolean"
    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_empty):
        return "integer"
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_empty):
        return "numeric"
    if all(isinstance(value, date) or isinstance(value, str) and _is_iso_date(value) for value in non_empty):
        return "date"
    return "text"


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False
