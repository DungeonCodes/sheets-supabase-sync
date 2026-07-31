from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from .hashing import deterministic_hash
from .models import Column, Record, Snapshot
from .normalization import infer_type, normalize_row


def build_snapshot(source_id: str, rows: Iterable[Mapping[str, Any]], key_column: str) -> Snapshot:
    normalized = [normalize_row(row) for row in rows]
    keys = [row.get(key_column) for row in normalized]
    if any(key in (None, "") for key in keys):
        raise ValueError(f"Coluna-chave ausente: {key_column}")
    all_columns = sorted({column for row in normalized for column in row})
    columns = [Column(name, infer_type([row.get(name) for row in normalized])) for name in all_columns]
    records = {
        str(row[key_column]): Record(str(row[key_column]), row, deterministic_hash(row))
        for row in normalized
    }
    return Snapshot(source_id, columns, records, datetime.now(UTC).isoformat())


def snapshot_to_dict(snapshot: Snapshot) -> dict[str, Any]:
    return {"source_id": snapshot.source_id, "created_at": snapshot.created_at,
            "columns": [{"name": c.name, "inferred_type": c.inferred_type} for c in snapshot.columns],
            "records": {key: {"key": r.key, "values": r.values, "row_hash": r.row_hash} for key, r in snapshot.records.items()}}


def snapshot_from_dict(data: Mapping[str, Any]) -> Snapshot:
    return Snapshot(str(data["source_id"]), [Column(**c) for c in data["columns"]],
                    {key: Record(**record) for key, record in data["records"].items()}, str(data["created_at"]))
