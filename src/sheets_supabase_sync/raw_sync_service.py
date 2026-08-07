from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from .errors import ErrorCode, SyncError
from .observability import log_event
from .raw_repository import RawStateRepository
from .raw_sync import RawChangePlan, RawInputRow, RawSnapshot, RawSyncSource, build_raw_snapshot, compare_raw_snapshots


@dataclass(frozen=True)
class RawSyncMetrics:
    rows_read: int
    rows_persisted: int
    duration_ms: int


@dataclass(frozen=True)
class RawSyncResult:
    plan: RawChangePlan
    metrics: RawSyncMetrics
    persisted: bool


class RawSynchronizationService:
    def __init__(self, repository: RawStateRepository | None = None, logger: logging.Logger | None = None) -> None:
        self._repository = repository
        self._logger = logger or logging.getLogger(__name__)

    def dry_run(
        self,
        source: RawSyncSource,
        header: Sequence[str],
        rows: Sequence[RawInputRow],
        read_at: datetime,
        previous: RawSnapshot | None = None,
        duration_ms: int = 0,
    ) -> RawSyncResult:
        snapshot = build_raw_snapshot(source, header, rows, read_at)
        plan = compare_raw_snapshots(snapshot, previous)
        return RawSyncResult(plan, RawSyncMetrics(len(rows), 0, duration_ms), False)

    def persist_locally(
        self,
        source: RawSyncSource,
        header: Sequence[str],
        rows: Sequence[RawInputRow],
        read_at: datetime,
        duration_ms: int = 0,
    ) -> RawSyncResult:
        if self._repository is None:
            raise SyncError(ErrorCode.DATABASE, "Repositorio raw nao configurado")
        if not self._repository.try_acquire(source.source_hash):
            raise SyncError(ErrorCode.VALIDATION, "Fonte ja possui execucao em andamento")
        previous = self._repository.load_snapshot(source.source_hash)
        run_id: str | None = None
        run_attempted = False
        try:
            plan = self.dry_run(source, header, rows, read_at, previous, duration_ms).plan
            run_attempted = True
            run_id = self._repository.start_run(source.source_hash, plan.snapshot.snapshot_hash)
            self._repository.append_history(source.source_hash, run_id, plan)
            self._repository.commit(source.source_hash, run_id, plan)
            self._repository.finish_run(run_id)
        except Exception as error:
            if run_attempted:
                self._repository.rollback(source.source_hash, run_id)
            self._log(source, "raw_sync_failed", "failed", plan=None, duration_ms=duration_ms, error=error)
            raise
        finally:
            self._repository.release(source.source_hash)
        self._log(source, "raw_sync_persisted", "success", plan=plan, duration_ms=duration_ms)
        return RawSyncResult(plan, RawSyncMetrics(len(rows), _persisted_count(plan), duration_ms), True)

    def _log(
        self,
        source: RawSyncSource,
        event: str,
        status: str,
        plan: RawChangePlan | None,
        duration_ms: int,
        error: BaseException | None = None,
    ) -> None:
        counts = plan.counts if plan else {}
        log_event(
            self._logger,
            event,
            status=status,
            data_source_id=source.source_hash[:12],
            duration_ms=duration_ms,
            rows_inserted=counts.get("new", 0),
            rows_updated=counts.get("changed", 0),
            rows_deleted=counts.get("removed", 0),
            rows_restored=counts.get("restored", 0),
            rows_unchanged=counts.get("unchanged", 0),
            error_code=error.code.value if isinstance(error, SyncError) else None,
        )


def _persisted_count(plan: RawChangePlan) -> int:
    return len(plan.new) + len(plan.changed) + len(plan.removed) + len(plan.restored)
