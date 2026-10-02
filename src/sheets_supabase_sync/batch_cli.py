from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from .config import load_institution_config
from .dispatcher import DispatchSummary, dispatch_sources, load_operational_sources, select_sources_due, source_statuses, summarize_dispatch
from .environment import Environment, load_environment
from .errors import SyncError
from .raw_sync_service import RawSyncResult
from .sources import DataSource, InstitutionConfig
from .staging_cli import _execute_operation
from .staging_guard import validate_staging_access
from .staging_sync import StagingSyncMode


EnvironmentLoader = Callable[[Path], Environment]
InstitutionLoader = Callable[[Path], InstitutionConfig]
StateLoader = Callable[[str, Sequence[DataSource]], dict]
Operation = Callable[[Path, Environment, DataSource, StagingSyncMode], RawSyncResult]
Emitter = Callable[[str], None]


def run_cli(
    arguments: Sequence[str],
    *,
    root: Path | None = None,
    environment_loader: EnvironmentLoader = load_environment,
    institution_loader: InstitutionLoader = load_institution_config,
    state_loader: StateLoader = load_operational_sources,
    operation: Operation = _execute_operation,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    emit: Emitter = print,
) -> int:
    parser = argparse.ArgumentParser(description="Dispatcher central de fontes staging elegiveis.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--mode", choices=(StagingSyncMode.APPLY_STAGING,), default=StagingSyncMode.APPLY_STAGING)
    parser.add_argument("--confirm-staging", action="store_true")
    parser.add_argument("--dry-select", action="store_true")
    args = parser.parse_args(list(arguments))
    selected_root = root or Path.cwd()
    try:
        environment = environment_loader(selected_root)
        validate_staging_access(environment, write_requested=not args.dry_select, confirmed=args.confirm_staging)
        sources = institution_loader(args.config).sources
        selections = select_sources_due(sources, state_loader(environment.db_url, sources), now())
        if args.dry_select:
            summary = summarize_dispatch(selections, ())
            statuses = source_statuses(selections, ())
        else:
            outcomes, summary = dispatch_sources(
                selections,
                lambda source: operation(selected_root, environment, source, StagingSyncMode.APPLY_STAGING),
            )
            statuses = source_statuses(selections, outcomes)
    except Exception as error:
        category = error.code.value if isinstance(error, SyncError) else "internal"
        emit(json.dumps({"status": "failed", "category": category}, sort_keys=True))
        return 2
    emit(json.dumps(_safe_summary(summary, statuses, dry_select=args.dry_select), sort_keys=True))
    return 0


def _safe_summary(summary: DispatchSummary, statuses: list[dict[str, str]], *, dry_select: bool) -> dict[str, object]:
    return {"environment": "staging", "mode": "dry_select" if dry_select else "apply_staging", "status": "selected" if dry_select else "completed", "sources": statuses, **summary.as_dict()}


def main() -> None:
    raise SystemExit(run_cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
