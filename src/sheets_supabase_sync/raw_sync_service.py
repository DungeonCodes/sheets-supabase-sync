from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from .errors import ErrorCode, SyncError
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
    def __init__(self, repository: RawStateRepository | None = None) -> None:
        self._repository = repository

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
        try:
            draft = self.dry_run(source, header, rows, read_at, previous, duration_ms)
            run_id = self._repository.start_run(source.source_hash, draft.plan.snapshot.snapshot_hash)
            result = draft
            self._repository.commit(source.source_hash, result.plan)
            self._repository.finish_run(run_id)
            return RawSyncResult(result.plan, RawSyncMetrics(len(rows), _persisted_count(result.plan), duration_ms), True)
        except Exception:
            self._repository.rollback(source.source_hash, previous, run_id)
            raise
        finally:
            self._repository.release(source.source_hash)


def _persisted_count(plan: RawChangePlan) -> int:
    return len(plan.new) + len(plan.changed) + len(plan.removed) + len(plan.restored)
