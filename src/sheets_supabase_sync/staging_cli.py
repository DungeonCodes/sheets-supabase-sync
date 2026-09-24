from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from .config import load_institution_config
from .environment import Environment, load_environment
from .errors import SyncError
from .google_config import load_google_sheets_config_for_source
from .google_sheets import GoogleSheetsReader
from .google_transport import GoogleHttpTransport
from .raw_repository import PostgresRawRepository, assess_raw_schema
from .raw_sync_service import RawSyncResult
from .sources import DataSource, InstitutionConfig
from .staging_guard import validate_staging_access
from .staging_sync import StagingSyncMode, StagingSyncOrchestrator


EnvironmentLoader = Callable[[Path], Environment]
InstitutionLoader = Callable[[Path], InstitutionConfig]
Operation = Callable[[Path, Environment, DataSource, StagingSyncMode], RawSyncResult]
Emitter = Callable[[str], None]


def run_cli(
    arguments: Sequence[str],
    *,
    root: Path | None = None,
    environment_loader: EnvironmentLoader = load_environment,
    institution_loader: InstitutionLoader = load_institution_config,
    operation: Operation | None = None,
    emit: Emitter = print,
) -> int:
    parser = argparse.ArgumentParser(description="Sincronizacao Google para PostgreSQL staging, com opt-in explicito.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--mode", choices=tuple(StagingSyncMode), default=StagingSyncMode.DRY_RUN)
    parser.add_argument("--confirm-staging", action="store_true")
    args = parser.parse_args(list(arguments))
    selected_root = root or Path.cwd()
    mode = StagingSyncMode(args.mode)
    try:
        environment = environment_loader(selected_root)
        validate_staging_access(
            environment,
            write_requested=mode is StagingSyncMode.APPLY_STAGING,
            confirmed=args.confirm_staging,
        )
        source = _select_source(institution_loader(args.config), args.source)
        result = (operation or _execute_operation)(selected_root, environment, source, mode)
    except Exception as error:
        category = error.code.value if isinstance(error, SyncError) else "internal"
        emit(json.dumps({"status": "failed", "category": category}, sort_keys=True))
        return 2
    emit(json.dumps(_safe_summary(source, mode, result), sort_keys=True))
    return 0


def _select_source(config: InstitutionConfig, name: str) -> DataSource:
    matches = [source for source in config.sources if source.name == name]
    if len(matches) != 1:
        raise ValueError("Fonte solicitada ausente ou ambigua")
    return matches[0]


def _execute_operation(
    root: Path,
    environment: Environment,
    source: DataSource,
    mode: StagingSyncMode,
) -> RawSyncResult:
    google = load_google_sheets_config_for_source(root, source.spreadsheet_id, source.sheet_name)
    reader = GoogleSheetsReader(
        GoogleHttpTransport(google.credential_file),
        retry_policy=google.retry_policy,
        timeout_seconds=google.timeout_seconds,
    )
    migrations = "\n".join(path.read_text(encoding="utf-8") for path in sorted((root / "supabase" / "migrations").glob("*.sql")))
    repository = PostgresRawRepository(assess_raw_schema(migrations), environment.db_url)
    return StagingSyncOrchestrator(reader, repository).run(source, mode, google.optional_range)


def _safe_summary(source: DataSource, mode: StagingSyncMode, result: RawSyncResult) -> dict[str, object]:
    return {
        "source": source.name,
        "environment": "staging",
        "mode": mode.value,
        "status": "applied" if result.persisted else "dry_run",
        "snapshot_rows": result.metrics.rows_read,
        "persisted_rows": result.metrics.rows_persisted,
        "counts": result.plan.counts,
        "reconciliation": result.reconciliation,
    }


def main() -> None:
    raise SystemExit(run_cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
