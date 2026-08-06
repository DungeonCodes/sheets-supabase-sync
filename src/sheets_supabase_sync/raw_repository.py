from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .errors import ErrorCode, SyncError
from .raw_sync import RawChangePlan, RawSnapshot


@dataclass(frozen=True)
class RawSchemaAssessment:
    supports_phase_2a: bool
    missing_capabilities: tuple[str, ...]


def assess_raw_schema(schema_sql: str) -> RawSchemaAssessment:
    normalized = schema_sql.lower()
    required = {
        "raw_import_rows.data_source_id": "data_source_id uuid not null",
        "raw_import_rows.row_key_hash": "row_key_hash text not null",
        "raw_import_rows.current-state uniqueness": "unique (data_source_id, row_key_hash)",
        "raw_import_rows.logical deletion": "deleted_at",
        "raw_import_rows.version identity": "unique (data_source_id, row_key_hash, content_hash)",
    }
    missing = tuple(name for name, token in required.items() if token not in normalized)
    return RawSchemaAssessment(not missing, missing)


class RawStateRepository(Protocol):
    def try_acquire(self, source_hash: str) -> bool: ...

    def release(self, source_hash: str) -> None: ...

    def load_snapshot(self, source_hash: str) -> RawSnapshot | None: ...

    def start_run(self, source_hash: str, snapshot_hash: str) -> str: ...

    def commit(self, source_hash: str, plan: RawChangePlan) -> None: ...

    def finish_run(self, run_id: str) -> None: ...

    def rollback(self, source_hash: str, previous: RawSnapshot | None, run_id: str | None) -> None: ...


class InMemoryRawStateRepository:
    def __init__(self, fail_on_start: bool = False, fail_on_commit: bool = False, fail_on_finish: bool = False) -> None:
        self._snapshots: dict[str, RawSnapshot] = {}
        self._locks: set[str] = set()
        self._runs: dict[str, str] = {}
        self._next_run = 1
        self._fail_on_start = fail_on_start
        self._fail_on_commit = fail_on_commit
        self._fail_on_finish = fail_on_finish

    def try_acquire(self, source_hash: str) -> bool:
        if source_hash in self._locks:
            return False
        self._locks.add(source_hash)
        return True

    def release(self, source_hash: str) -> None:
        self._locks.discard(source_hash)

    def load_snapshot(self, source_hash: str) -> RawSnapshot | None:
        return self._snapshots.get(source_hash)

    def start_run(self, source_hash: str, snapshot_hash: str) -> str:
        if self._fail_on_start:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada ao iniciar execucao")
        run_id = f"run-{self._next_run}"
        self._next_run += 1
        self._runs[run_id] = "running"
        return run_id

    def commit(self, source_hash: str, plan: RawChangePlan) -> None:
        if self._fail_on_commit:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada antes do commit")
        from .raw_sync import apply_tombstones

        self._snapshots[source_hash] = apply_tombstones(plan)

    def finish_run(self, run_id: str) -> None:
        if self._fail_on_finish:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada ao finalizar execucao")
        self._runs[run_id] = "applied"

    def rollback(self, source_hash: str, previous: RawSnapshot | None, run_id: str | None) -> None:
        if previous is None:
            self._snapshots.pop(source_hash, None)
        else:
            self._snapshots[source_hash] = previous
        if run_id:
            self._runs[run_id] = "failed"


class PostgresRawRepository:
    """Limite de persistência PostgreSQL; não abre conexão nem executa SQL nesta fase."""

    def __init__(self, assessment: RawSchemaAssessment) -> None:
        self._assessment = assessment

    def assert_supported(self) -> None:
        if not self._assessment.supports_phase_2a:
            raise SyncError(ErrorCode.SCHEMA, "Schema raw atual nao suporta estado idempotente; migration incremental obrigatoria")

    @staticmethod
    def find_source_sql() -> str:
        return "SELECT id FROM public.data_sources WHERE spreadsheet_id = %s AND sheet_name = %s"

    @staticmethod
    def register_source_sql() -> str:
        return (
            "INSERT INTO public.data_sources (name, spreadsheet_id, sheet_name, target_table, business_key) "
            "VALUES (%s, %s, %s, %s, %s::jsonb) "
            "ON CONFLICT (spreadsheet_id, sheet_name) DO UPDATE SET updated_at = now() RETURNING id"
        )

    @staticmethod
    def start_run_sql() -> str:
        return (
            "INSERT INTO public.sync_runs "
            "(data_source_id, status, snapshot_hash, schema_metadata) "
            "VALUES (%s, 'running', %s, %s::jsonb) RETURNING id"
        )

    @staticmethod
    def append_raw_row_sql() -> str:
        return (
            "INSERT INTO public.raw_import_rows "
            "(data_source_id, sync_run_id, source_row_number, row_key_hash, content_hash, payload_json) "
            "VALUES (%s, %s, %s, %s, %s, %s::jsonb)"
        )

    @staticmethod
    def finish_run_sql() -> str:
        return (
            "UPDATE public.sync_runs SET status = %s, finished_at = now(), inserted_rows = %s, "
            "updated_rows = %s, deleted_rows = %s, restored_rows = %s, unchanged_rows = %s "
            "WHERE id = %s"
        )

    @staticmethod
    def record_error_sql() -> str:
        return (
            "INSERT INTO public.import_errors (data_source_id, sync_run_id, error_type, error_message, row_number) "
            "VALUES (%s, %s, %s, %s, %s)"
        )

    @staticmethod
    def update_source_success_sql() -> str:
        return (
            "UPDATE public.data_sources SET last_success_at = now(), consecutive_failures = 0, "
            "last_duration_ms = %s, last_rows_read = %s, last_rows_inserted = %s, "
            "last_rows_updated = %s, last_rows_deleted = %s, last_rows_restored = %s "
            "WHERE id = %s"
        )

    @staticmethod
    def update_source_failure_sql() -> str:
        return (
            "UPDATE public.data_sources SET last_failure_at = now(), consecutive_failures = consecutive_failures + 1, "
            "last_error_code = %s, last_error_summary = %s WHERE id = %s"
        )

    @staticmethod
    def try_lock_sql() -> str:
        return "SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0))"
