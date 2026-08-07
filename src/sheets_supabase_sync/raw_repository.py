from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Protocol

from .errors import ErrorCode, SyncError
from .raw_state import RawCurrentRow, RawStateOperation, apply_state_command, history_change_type, plan_state_commands
from .raw_sync import RawChangePlan, RawRecord, RawSnapshot, compute_snapshot_hash


@dataclass(frozen=True)
class RawSchemaAssessment:
    supports_phase_2a: bool
    missing_capabilities: tuple[str, ...]


def assess_raw_schema(schema_sql: str) -> RawSchemaAssessment:
    """Avalia o DDL declarado nas migrations; nao inspeciona o catalogo remoto."""
    normalized = schema_sql.lower()
    required = {
        "raw_current_rows.table": "create table public.raw_current_rows",
        "raw_current_rows.source_key_identity": "unique (data_source_id, row_key_hash)",
        "raw_current_rows.logical_deletion": "deleted_at",
        "raw_current_rows.version_identity": "version integer not null",
        "raw_current_rows.run_traceability": "last_sync_run_id",
    }
    missing = tuple(name for name, token in required.items() if token not in normalized)
    return RawSchemaAssessment(not missing, missing)


@dataclass(frozen=True)
class RawHistoryEntry:
    run_id: str
    key_hash: str
    change_type: str
    source_row_number: int


class RawStateRepository(Protocol):
    def try_acquire(self, source_hash: str) -> bool: ...

    def release(self, source_hash: str) -> None: ...

    def load_snapshot(self, source_hash: str) -> RawSnapshot | None: ...

    def start_run(self, source_hash: str, snapshot_hash: str) -> str: ...

    def append_history(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None: ...

    def commit(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None: ...

    def finish_run(self, run_id: str) -> None: ...

    def rollback(self, source_hash: str, run_id: str | None) -> None: ...


@dataclass
class _StoredSource:
    header: tuple[str, ...]
    created_at: datetime
    rows: dict[str, RawCurrentRow] = field(default_factory=dict)
    payloads: dict[str, Mapping[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class _Checkpoint:
    source: _StoredSource | None
    history_length: int


class InMemoryRawStateRepository:
    """Referencia local da semantica transacional; nao abre conexao PostgreSQL."""

    def __init__(
        self,
        fail_on_start: bool = False,
        fail_on_history: bool = False,
        fail_on_commit: bool = False,
        fail_on_finish: bool = False,
    ) -> None:
        self._sources: dict[str, _StoredSource] = {}
        self._checkpoints: dict[str, _Checkpoint] = {}
        self._history: list[RawHistoryEntry] = []
        self._locks: set[str] = set()
        self._runs: dict[str, str] = {}
        self._next_run = 1
        self._fail_on_start = fail_on_start
        self._fail_on_history = fail_on_history
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
        stored = self._sources.get(source_hash)
        if stored is None:
            return None
        records = {
            key_hash: RawRecord(row.source_row_number, key_hash, row.content_hash, stored.payloads[key_hash], row.is_deleted)
            for key_hash, row in stored.rows.items()
        }
        snapshot_hash = compute_snapshot_hash(source_hash, stored.header, records.values())
        return RawSnapshot(source_hash, stored.header, records, snapshot_hash, stored.created_at)

    def current_rows(self, source_hash: str) -> Mapping[str, RawCurrentRow]:
        stored = self._sources.get(source_hash)
        return dict(stored.rows) if stored else {}

    def history(self) -> tuple[RawHistoryEntry, ...]:
        return tuple(self._history)

    def run_status(self, run_id: str) -> str | None:
        return self._runs.get(run_id)

    def start_run(self, source_hash: str, snapshot_hash: str) -> str:
        self._checkpoints[source_hash] = _Checkpoint(deepcopy(self._sources.get(source_hash)), len(self._history))
        if self._fail_on_start:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada ao iniciar execucao")
        run_id = f"run-{self._next_run}"
        self._next_run += 1
        self._runs[run_id] = "running"
        return run_id

    def append_history(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None:
        if self._fail_on_history:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada ao registrar historico")
        for command in plan_state_commands(plan):
            change_type = history_change_type(command.operation)
            if change_type is not None:
                self._history.append(RawHistoryEntry(run_id, command.record.key_hash, change_type, command.record.source_row_number))

    def commit(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None:
        if self._fail_on_commit:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada antes do commit")
        stored = self._sources.setdefault(source_hash, _StoredSource(plan.snapshot.header, plan.snapshot.created_at))
        stored.header = plan.snapshot.header
        for command in plan_state_commands(plan):
            key_hash = command.record.key_hash
            stored.rows[key_hash] = apply_state_command(stored.rows.get(key_hash), command)
            if command.operation is not RawStateOperation.TOMBSTONE:
                stored.payloads[key_hash] = dict(command.record.values)

    def finish_run(self, run_id: str) -> None:
        if self._fail_on_finish:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada ao finalizar execucao")
        self._runs[run_id] = "applied"

    def rollback(self, source_hash: str, run_id: str | None) -> None:
        checkpoint = self._checkpoints.pop(source_hash, None)
        if checkpoint is None:
            return
        if checkpoint.source is None:
            self._sources.pop(source_hash, None)
        else:
            self._sources[source_hash] = checkpoint.source
        del self._history[checkpoint.history_length :]
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
            "(data_source_id, sync_run_id, source_row_number, row_key_hash, content_hash, payload_json, change_type, row_version) "
            "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)"
        )

    @staticmethod
    def load_current_state_sql() -> str:
        return (
            "SELECT row_key_hash, content_hash, source_row_number, is_deleted, version "
            "FROM public.raw_current_rows WHERE data_source_id = %s"
        )

    @staticmethod
    def insert_current_row_sql() -> str:
        return (
            "INSERT INTO public.raw_current_rows "
            "(data_source_id, row_key_hash, content_hash, payload_json, source_row_number, last_sync_run_id) "
            "VALUES (%s, %s, %s, %s::jsonb, %s, %s)"
        )

    @staticmethod
    def update_current_row_sql() -> str:
        return (
            "UPDATE public.raw_current_rows SET content_hash = %s, payload_json = %s::jsonb, "
            "source_row_number = %s, version = version + 1, last_seen_at = now(), updated_at = now(), "
            "last_sync_run_id = %s "
            "WHERE data_source_id = %s AND row_key_hash = %s AND NOT is_deleted"
        )

    @staticmethod
    def tombstone_current_row_sql() -> str:
        return (
            "UPDATE public.raw_current_rows SET is_deleted = true, deleted_at = now(), "
            "version = version + 1, updated_at = now(), last_sync_run_id = %s "
            "WHERE data_source_id = %s AND row_key_hash = %s AND NOT is_deleted"
        )

    @staticmethod
    def restore_current_row_sql() -> str:
        return (
            "UPDATE public.raw_current_rows SET is_deleted = false, deleted_at = NULL, "
            "content_hash = %s, payload_json = %s::jsonb, source_row_number = %s, "
            "version = version + 1, last_seen_at = now(), updated_at = now(), last_sync_run_id = %s "
            "WHERE data_source_id = %s AND row_key_hash = %s AND is_deleted"
        )

    @staticmethod
    def touch_current_row_sql() -> str:
        return (
            "UPDATE public.raw_current_rows SET last_seen_at = now(), source_row_number = %s, "
            "last_sync_run_id = %s "
            "WHERE data_source_id = %s AND row_key_hash = %s AND NOT is_deleted"
        )

    @staticmethod
    def state_command_sql(operation: RawStateOperation) -> str:
        return {
            RawStateOperation.INSERT: PostgresRawRepository.insert_current_row_sql(),
            RawStateOperation.UPDATE: PostgresRawRepository.update_current_row_sql(),
            RawStateOperation.TOMBSTONE: PostgresRawRepository.tombstone_current_row_sql(),
            RawStateOperation.RESTORE: PostgresRawRepository.restore_current_row_sql(),
            RawStateOperation.TOUCH: PostgresRawRepository.touch_current_row_sql(),
        }[operation]

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
