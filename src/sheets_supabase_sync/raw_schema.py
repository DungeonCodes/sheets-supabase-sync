from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .hashing import deterministic_hash


@dataclass(frozen=True)
class RawSchema:
    columns: tuple[str, ...]

    @classmethod
    def from_header(cls, header: Sequence[str]) -> "RawSchema":
        return cls(tuple(header))

    @property
    def fingerprint(self) -> str:
        return deterministic_hash({"columns": tuple(sorted(self.columns))})

    def as_json(self) -> dict[str, object]:
        return {"columns": list(self.columns), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class RawSchemaChange:
    previous: RawSchema
    proposed: RawSchema
    added: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def is_reorder(self) -> bool:
        return not self.added and not self.removed and self.previous.columns != self.proposed.columns

    @property
    def is_blocking(self) -> bool:
        return bool(self.added or self.removed)

    @property
    def change_type(self) -> str:
        if self.added and self.removed:
            return "blocked_header_changed"
        if self.added:
            return "blocked_column_added"
        return "blocked_column_removed"


def compare_raw_schemas(previous: RawSchema, proposed: RawSchema) -> RawSchemaChange:
    previous_columns = set(previous.columns)
    proposed_columns = set(proposed.columns)
    return RawSchemaChange(
        previous,
        proposed,
        tuple(sorted(proposed_columns - previous_columns)),
        tuple(sorted(previous_columns - proposed_columns)),
    )
