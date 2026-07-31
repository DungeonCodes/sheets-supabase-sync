from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SyncConfig:
    source_id: str
    key_column: str
    table_name: str
    local_host: str = "127.0.0.1"


def load_config(path: Path) -> SyncConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SyncConfig(**data)
