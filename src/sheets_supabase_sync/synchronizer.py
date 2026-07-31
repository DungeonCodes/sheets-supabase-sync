from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifacts import markdown_report, write_artifacts
from .config import SyncConfig
from .diff import compare, with_tombstones
from .executors import apply_sql_locally
from .snapshot import build_snapshot, snapshot_from_dict, snapshot_to_dict
from .sql_generator import generate_sql


def synchronize(
    rows: list[dict[str, Any]],
    config: SyncConfig,
    snapshot_path: Path,
    artifact_dir: Path,
    mode: str = "dry-run",
    database_url: str | None = None,
    allowed_hosts: set[str] | None = None,
) -> dict[str, Any]:
    if mode not in {"dry-run", "generate-sql", "apply-local"}:
        raise ValueError("Modo invalido")
    if mode == "apply-local" and not database_url:
        raise ValueError("apply-local exige --database-url explicita")
    current = build_snapshot(config.source_id, rows, config.key_column)
    try:
        previous = snapshot_from_dict(json.loads(snapshot_path.read_text(encoding="utf-8"))) if snapshot_path.exists() else None
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError("Snapshot invalido ou corrompido; interrompendo para evitar comparacao insegura.") from error
    result = compare(current, previous)
    sql = generate_sql(result, config.table_name, config.source_id)
    manifest = {"source_id": config.source_id, "mode": mode, "dry_run": mode != "apply-local", "counts": {"new": len(result.new), "changed": len(result.changed), "removed": len(result.removed), "restored": len(result.restored), "duplicates": len(result.duplicates)}, "schema_pending": {"new_columns": result.new_columns, "missing_columns": result.missing_columns, "possible_renames": result.possible_renames, "incompatible_types": result.incompatible_types}}
    write_artifacts(artifact_dir, manifest, markdown_report(result), sql)
    if mode == "apply-local":
        apply_sql_locally(sql, database_url, allowed_hosts)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshot_to_dict(with_tombstones(current, result.removed)), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
