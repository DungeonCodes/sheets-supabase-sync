from __future__ import annotations

from .hashing import deterministic_hash
from .models import DiffResult, Record, Snapshot


def compare(current: Snapshot, previous: Snapshot | None) -> DiffResult:
    if previous is None:
        result = DiffResult(new=list(current.records.values()))
        result.duplicates = _duplicates(current)
        return result
    result = DiffResult()
    previous_columns = {column.name: column.inferred_type for column in previous.columns}
    current_columns = {column.name: column.inferred_type for column in current.columns}
    result.new_columns = sorted(current_columns.keys() - previous_columns.keys())
    result.missing_columns = sorted(previous_columns.keys() - current_columns.keys())
    result.possible_renames = [(old, new) for old in result.missing_columns for new in result.new_columns
                               if old.replace("_", "") == new.replace("_", "") or old[:4] == new[:4]]
    result.incompatible_types = [(name, previous_columns[name], current_columns[name]) for name in previous_columns.keys() & current_columns.keys()
                                 if previous_columns[name] != current_columns[name]]
    for key, record in current.records.items():
        old = previous.records.get(key)
        if old is None:
            result.new.append(record)
        elif old.values.get("deleted", False):
            result.restored.append(record)
        elif old.row_hash != record.row_hash:
            result.changed.append(record)
    result.removed = [record for key, record in previous.records.items() if key not in current.records and not record.values.get("deleted", False)]
    result.duplicates = _duplicates(current)
    return result


def with_tombstones(current: Snapshot, removed: list[Record]) -> Snapshot:
    """Mantem exclusoes logicas no snapshot para distinguir restauracao de nova linha."""
    records = dict(current.records)
    for record in removed:
        values = {**record.values, "deleted": True}
        records[record.key] = Record(record.key, values, deterministic_hash(values))
    return Snapshot(current.source_id, current.columns, records, current.created_at)


def has_blocking_schema_change(result: DiffResult) -> bool:
    return bool(result.missing_columns or result.possible_renames or result.incompatible_types)


def _duplicates(snapshot: Snapshot) -> list[str]:
    hashes: dict[str, list[str]] = {}
    for record in snapshot.records.values():
        content = {name: value for name, value in record.values.items() if str(value) != record.key}
        hashes.setdefault(deterministic_hash(content), []).append(record.key)
    return sorted(key for keys in hashes.values() if len(keys) > 1 for key in keys)
