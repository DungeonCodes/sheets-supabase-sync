from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Column:
    name: str
    inferred_type: str = "text"


@dataclass(frozen=True)
class Record:
    key: str
    values: dict[str, Any]
    row_hash: str


@dataclass
class Snapshot:
    source_id: str
    columns: list[Column]
    records: dict[str, Record]
    created_at: str


@dataclass
class DiffResult:
    new: list[Record] = field(default_factory=list)
    changed: list[Record] = field(default_factory=list)
    removed: list[Record] = field(default_factory=list)
    restored: list[Record] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    new_columns: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    possible_renames: list[tuple[str, str]] = field(default_factory=list)
    incompatible_types: list[tuple[str, str, str]] = field(default_factory=list)
