from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .identifiers import validate_identifier


@dataclass(frozen=True)
class DataSource:
    name: str
    spreadsheet_id: str
    sheet_name: str
    target_table: str
    business_key: tuple[str, ...]
    sync_interval_minutes: int
    enabled: bool = True
    last_sync_at: datetime | None = None

    def __post_init__(self) -> None:
        validate_identifier(self.target_table)
        if not self.business_key:
            raise ValueError("business_key deve conter ao menos uma coluna")
        if self.sync_interval_minutes <= 0:
            raise ValueError("sync_interval_minutes deve ser positivo")

    def next_sync_at(self) -> datetime | None:
        if self.last_sync_at is None:
            return None
        return self.last_sync_at + timedelta(minutes=self.sync_interval_minutes)


@dataclass(frozen=True)
class InstitutionConfig:
    name: str
    project_mode: str
    sources: tuple[DataSource, ...]

    def __post_init__(self) -> None:
        if self.project_mode != "isolated":
            raise ValueError("Esta versao exige project_mode isolated")
        tables = [source.target_table for source in self.sources]
        if len(tables) != len(set(tables)):
            raise ValueError("Cada fonte deve possuir target_table propria")
