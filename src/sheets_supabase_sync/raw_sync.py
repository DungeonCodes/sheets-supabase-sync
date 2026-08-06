from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from .errors import ErrorCode, SyncError
from .hashing import deterministic_hash
from .identifiers import validate_identifier


@dataclass(frozen=True)
class RawSyncSource:
    logical_name: str
    source_hash: str
    spreadsheet_id: str
    sheet_name: str
    target_table: str
    business_key: tuple[str, ...]

    def __post_init__(self) -> None:
        validate_identifier(self.target_table)
        if not self.logical_name or not self.source_hash or not self.business_key:
            raise SyncError(ErrorCode.CONFIGURATION, "Contrato de fonte raw invalido")


@dataclass(frozen=True)
class RawInputRow:
    source_row_number: int
    values: Mapping[str, str]


@dataclass(frozen=True)
class RawRecord:
    source_row_number: int
    key_hash: str
    content_hash: str
    values: Mapping[str, str]
    deleted: bool = False


@dataclass(frozen=True)
class RawSnapshot:
    source_hash: str
    header: tuple[str, ...]
    records: Mapping[str, RawRecord]
    snapshot_hash: str
    created_at: datetime


@dataclass(frozen=True)
class RawChangePlan:
    snapshot: RawSnapshot
    new: tuple[RawRecord, ...]
    changed: tuple[RawRecord, ...]
    removed: tuple[RawRecord, ...]
    restored: tuple[RawRecord, ...]
    unchanged: tuple[RawRecord, ...]

    @property
    def counts(self) -> dict[str, int]:
        return {
            "new": len(self.new),
            "changed": len(self.changed),
            "removed": len(self.removed),
            "restored": len(self.restored),
            "unchanged": len(self.unchanged),
        }


def build_raw_snapshot(
    source: RawSyncSource,
    header: Sequence[str],
    rows: Sequence[RawInputRow],
    read_at: datetime,
) -> RawSnapshot:
    normalized_header = tuple(header)
    if not normalized_header or len(normalized_header) != len(set(normalized_header)):
        raise SyncError(ErrorCode.SCHEMA, "Cabecalho raw invalido")
    for key in source.business_key:
        if key not in normalized_header:
            raise SyncError(ErrorCode.SCHEMA, "Chave de negocio ausente no cabecalho")
    records: dict[str, RawRecord] = {}
    for input_row in rows:
        values = {name: "" if input_row.values.get(name) is None else str(input_row.values.get(name, "")) for name in normalized_header}
        key_values = tuple(values[key].strip() for key in source.business_key)
        if any(not value for value in key_values):
            raise SyncError(ErrorCode.VALIDATION, "Chave de negocio vazia")
        key_hash = deterministic_hash({"business_key": key_values})
        if key_hash in records:
            raise SyncError(ErrorCode.VALIDATION, "Chave de negocio duplicada")
        content_hash = deterministic_hash(values)
        records[key_hash] = RawRecord(input_row.source_row_number, key_hash, content_hash, values)
    snapshot_hash = deterministic_hash({
        "source_hash": source.source_hash,
        "header": normalized_header,
        "records": [
            {"key_hash": record.key_hash, "content_hash": record.content_hash, "deleted": record.deleted}
            for record in sorted(records.values(), key=lambda item: item.key_hash)
        ],
    })
    return RawSnapshot(source.source_hash, normalized_header, records, snapshot_hash, read_at)


def compare_raw_snapshots(current: RawSnapshot, previous: RawSnapshot | None) -> RawChangePlan:
    if previous is None:
        return RawChangePlan(current, tuple(current.records.values()), (), (), (), ())
    new: list[RawRecord] = []
    changed: list[RawRecord] = []
    restored: list[RawRecord] = []
    unchanged: list[RawRecord] = []
    for key_hash, record in current.records.items():
        prior = previous.records.get(key_hash)
        if prior is None:
            new.append(record)
        elif prior.deleted:
            restored.append(record)
        elif prior.content_hash != record.content_hash:
            changed.append(record)
        else:
            unchanged.append(record)
    removed = [record for key_hash, record in previous.records.items() if key_hash not in current.records and not record.deleted]
    return RawChangePlan(current, tuple(new), tuple(changed), tuple(removed), tuple(restored), tuple(unchanged))


def apply_tombstones(plan: RawChangePlan) -> RawSnapshot:
    records = dict(plan.snapshot.records)
    for record in plan.removed:
        tombstone_values = dict(record.values)
        records[record.key_hash] = RawRecord(
            record.source_row_number,
            record.key_hash,
            record.content_hash,
            tombstone_values,
            deleted=True,
        )
    snapshot_hash = deterministic_hash({
        "source_hash": plan.snapshot.source_hash,
        "header": plan.snapshot.header,
        "records": [
            {"key_hash": record.key_hash, "content_hash": record.content_hash, "deleted": record.deleted}
            for record in sorted(records.values(), key=lambda item: item.key_hash)
        ],
    })
    return RawSnapshot(plan.snapshot.source_hash, plan.snapshot.header, records, snapshot_hash, plan.snapshot.created_at)
