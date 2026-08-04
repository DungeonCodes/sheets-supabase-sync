from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .sources import DataSource, InstitutionConfig

@dataclass(frozen=True)
class SyncConfig:
    source_id: str
    key_column: str
    table_name: str
    local_host: str = "127.0.0.1"


def load_config(path: Path) -> SyncConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SyncConfig(**data)


def load_institution_config(path: Path) -> InstitutionConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    institution = data["institution"]
    supabase = data["supabase"]
    sources = tuple(
        DataSource(
            name=source["name"],
            spreadsheet_id=source["spreadsheet_id"],
            sheet_name=source["sheet_name"],
            target_table=source["target_table"],
            business_key=tuple(source["business_key"]),
            sync_interval_minutes=source["sync_interval_minutes"],
            enabled=source.get("enabled", True),
        )
        for source in data["sources"]
    )
    return InstitutionConfig(institution["name"], supabase["project_mode"], sources)
