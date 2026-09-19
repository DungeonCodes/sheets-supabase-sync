from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from random import random
from time import monotonic, sleep
from typing import Sequence
from uuid import uuid4

from .errors import ErrorCode, SyncError
from .observability import log_event
from .operational_failures import DatabaseStage, postgres_sync_error
from .raw_repository import RawStateRepository, ReconciliationOutcome
from .raw_schema import RawSchema, compare_raw_schemas
from .raw_sync import RawChangePlan, RawInputRow, RawSnapshot, RawSyncSource, build_raw_snapshot, compare_raw_snapshots
from .retries import RetryNotice, RetryPolicy, retry


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
    reconciliation: str = "not_required"


class RawSynchronizationService:
    def __init__(
        self,
        repository: RawStateRepository | None = None,
        logger: logging.Logger | None = None,
        *,
        retry_policy: RetryPolicy = RetryPolicy(max_attempts=3, base_delay_seconds=0.25, max_delay_seconds=2, max_elapsed_seconds=8),
        pause: Callable[[float], None] = sleep,
        random_value: Callable[[], float] = random,
        monotonic_clock: Callable[[], float] = monotonic,
        execution_id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._repository = repository
        self._logger = logger or logging.getLogger(__name__)
        self._retry_policy = retry_policy
        self._pause = pause
        self._random_value = random_value
        self._monotonic_clock = monotonic_clock
        self._execution_id_factory = execution_id_factory

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

    def persist(
        self,
        source: RawSyncSource,
        header: Sequence[str],
        rows: Sequence[RawInputRow],
        read_at: datetime,
        duration_ms: int = 0,
    ) -> RawSyncResult:
        if self._repository is None:
            raise SyncError(ErrorCode.DATABASE, "Repositorio raw nao configurado")
        snapshot = build_raw_snapshot(source, header, rows, read_at)
        execution_id = self._execution_id_factory()
        attempt = 0

        def operation() -> RawSyncResult:
            nonlocal attempt
            attempt += 1
            return self._persist_attempt(source, snapshot, rows, read_at, duration_ms, execution_id, attempt)

        return retry(
            operation,
            policy=self._retry_policy,
            pause=self._pause,
            random_value=self._random_value,
            monotonic_clock=self._monotonic_clock,
            on_retry=lambda notice: self._log_retry(source, notice),
        )

    def persist_locally(
        self,
        source: RawSyncSource,
        header: Sequence[str],
        rows: Sequence[RawInputRow],
        read_at: datetime,
        duration_ms: int = 0,
    ) -> RawSyncResult:
        """Alias mantido para compatibilidade com os fluxos e testes locais existentes."""
        return self.persist(source, header, rows, read_at, duration_ms)

    def _persist_attempt(
        self,
        source: RawSyncSource,
        snapshot: RawSnapshot,
        rows: Sequence[RawInputRow],
        read_at: datetime,
        duration_ms: int,
        execution_id: str,
        attempt: int,
    ) -> RawSyncResult:
        assert self._repository is not None
        if not self._repository.try_acquire(source.source_hash):
            error = SyncError(ErrorCode.BUSY, "Fonte ja possui execucao em andamento")
            self._log(source, "raw_sync_deferred", "busy_deferred", plan=None, duration_ms=duration_ms, attempt=attempt, error=error)
            raise error
        run_id: str | None = None
        plan: RawChangePlan | None = None
        try:
            self._repository.prepare_source(source)
            baseline_schema = self._repository.load_schema(source.source_hash)
            proposed_schema = RawSchema.from_header(snapshot.header)
            if baseline_schema is not None:
                schema_change = compare_raw_schemas(baseline_schema, proposed_schema)
                if schema_change.is_blocking:
                    self._repository.record_schema_change(schema_change)
                    self._repository.commit_transaction(source.source_hash, "")
                    raise SyncError(ErrorCode.SCHEMA, "Schema da fonte divergiu; revisao humana obrigatoria")
            previous = self._repository.load_snapshot(source.source_hash, snapshot.header, read_at)
            plan = compare_raw_snapshots(snapshot, previous)
            run_id = self._repository.start_run(source.source_hash, plan.snapshot.snapshot_hash, execution_id)
            self._repository.append_history(source.source_hash, run_id, plan)
            self._repository.set_active_plan(plan)
            self._repository.apply_plan(source.source_hash, run_id, plan)
            self._repository.finish_run(run_id)
            self._repository.commit_transaction(source.source_hash, run_id)
        except Exception as error:
            classified = error if isinstance(error, SyncError) else postgres_sync_error(error, DatabaseStage.TRANSACTION)
            if classified.code is ErrorCode.AMBIGUOUS_OUTCOME and plan is not None:
                self._repository.release(source.source_hash)
                reconciliation = self._repository.reconcile_run(source, execution_id, plan)
                if reconciliation is ReconciliationOutcome.APPLIED:
                    self._log(source, "raw_sync_reconciled", "success", plan=plan, duration_ms=duration_ms, attempt=attempt)
                    return RawSyncResult(plan, RawSyncMetrics(len(rows), _persisted_count(plan), duration_ms), True, reconciliation.value)
                if reconciliation is ReconciliationOutcome.NOT_PERSISTED:
                    classified = SyncError(ErrorCode.DATABASE_TRANSIENT, "Commit confirmado como nao persistido", True)
                else:
                    classified = SyncError(ErrorCode.AMBIGUOUS_OUTCOME, "Resultado do commit permanece inconclusivo")
            else:
                self._repository.rollback(source.source_hash, run_id)
            outcome = "ambiguous_outcome" if classified.code is ErrorCode.AMBIGUOUS_OUTCOME else "failed"
            self._log(source, "raw_sync_failed", outcome, plan=None, duration_ms=duration_ms, attempt=attempt, error=classified)
            raise classified from error
        finally:
            self._repository.release(source.source_hash)
        assert plan is not None
        self._log(source, "raw_sync_persisted", "success", plan=plan, duration_ms=duration_ms, attempt=attempt)
        return RawSyncResult(plan, RawSyncMetrics(len(rows), _persisted_count(plan), duration_ms), True)

    def _log_retry(self, source: RawSyncSource, notice: RetryNotice) -> None:
        log_event(
            self._logger,
            "raw_sync_retry",
            data_source_id=source.source_hash[:12],
            operation="postgres_transaction",
            attempt=notice.attempt,
            max_attempts=notice.max_attempts,
            error_category=notice.error_code,
            retryable=True,
            backoff_ms=round(notice.wait_seconds * 1000),
            duration_ms=round(notice.elapsed_seconds * 1000),
            outcome="retrying",
        )

    def _log(
        self,
        source: RawSyncSource,
        event: str,
        status: str,
        plan: RawChangePlan | None,
        duration_ms: int,
        attempt: int,
        error: BaseException | None = None,
    ) -> None:
        counts = plan.counts if plan else {}
        log_event(
            self._logger,
            event,
            status=status,
            operation="postgres_transaction",
            attempt=attempt,
            max_attempts=self._retry_policy.max_attempts,
            error_category=error.code.value if isinstance(error, SyncError) else None,
            retryable=error.retryable if isinstance(error, SyncError) else False if error else None,
            backoff_ms=0,
            outcome=status,
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
