from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Mapping, Protocol

import psycopg

from .errors import ErrorCode, SyncError
from .raw_state import RawCurrentRow, RawStateOperation, apply_state_command, history_change_type, plan_state_commands
from .raw_sync import RawChangePlan, RawRecord, RawSnapshot, RawSyncSource, compute_snapshot_hash


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
    source_row_number: int | None


class RawStateRepository(Protocol):
    def try_acquire(self, source_hash: str) -> bool: ...

    def release(self, source_hash: str) -> None: ...

    def prepare_source(self, source: RawSyncSource) -> None: ...

    def load_snapshot(
        self,
        source_hash: str,
        header: tuple[str, ...] = (),
        read_at: datetime | None = None,
    ) -> RawSnapshot | None: ...

    def start_run(self, source_hash: str, snapshot_hash: str) -> str: ...

    def append_history(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None: ...

    def commit(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None: ...

    def finish_run(self, run_id: str) -> None: ...

    def complete(self) -> None: ...

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

    def prepare_source(self, source: RawSyncSource) -> None:
        return None

    def load_snapshot(
        self,
        source_hash: str,
        header: tuple[str, ...] = (),
        read_at: datetime | None = None,
    ) -> RawSnapshot | None:
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

    def complete(self) -> None:
        return None

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
    """Unidade transacional PostgreSQL para estado raw e eventos."""

    def __init__(
        self,
        assessment: RawSchemaAssessment,
        database_url: str | None = None,
        failure_injector: Callable[[str], None] | None = None,
    ) -> None:
        self._assessment = assessment
        self._database_url = database_url
        self._failure_injector = failure_injector
        self._connection: psycopg.Connection | None = None
        self._data_source_id: str | None = None
        self._versions: dict[str, int] = {}

    def assert_supported(self) -> None:
        if not self._assessment.supports_phase_2a:
            raise SyncError(ErrorCode.SCHEMA, "Schema raw atual nao suporta estado idempotente; migration incremental obrigatoria")

    def try_acquire(self, source_hash: str) -> bool:
        self.assert_supported()
        if not self._database_url:
            raise SyncError(ErrorCode.CONFIGURATION, "URL PostgreSQL explicita obrigatoria")
        self._connection = psycopg.connect(self._database_url, autocommit=False)
        with self._connection.cursor() as cursor:
            cursor.execute(self.try_lock_sql(), (source_hash,))
            acquired = bool(cursor.fetchone()[0])
        if not acquired:
            self._connection.rollback()
            self.release(source_hash)
        return acquired

    def release(self, source_hash: str) -> None:
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        self._data_source_id = None
        self._versions = {}

    def prepare_source(self, source: RawSyncSource) -> None:
        cursor = self._cursor()
        cursor.execute(
            self.register_source_sql(),
            (
                source.logical_name,
                source.spreadsheet_id,
                source.sheet_name,
                source.target_table,
                json.dumps(source.business_key),
            ),
        )
        self._data_source_id = str(cursor.fetchone()[0])

    def load_snapshot(
        self,
        source_hash: str,
        header: tuple[str, ...] = (),
        read_at: datetime | None = None,
    ) -> RawSnapshot | None:
        cursor = self._cursor()
        cursor.execute(self.load_current_state_sql(), (self._require_source_id(),))
        records: dict[str, RawRecord] = {}
        self._versions = {}
        for key_hash, content_hash, row_number, deleted, version, payload in cursor.fetchall():
            records[key_hash] = RawRecord(row_number or 0, key_hash, content_hash, payload or {}, deleted)
            self._versions[key_hash] = version
        if not records:
            return None
        created_at = read_at or datetime.now().astimezone()
        return RawSnapshot(
            source_hash,
            header,
            records,
            compute_snapshot_hash(source_hash, header, records.values()),
            created_at,
        )

    def start_run(self, source_hash: str, snapshot_hash: str) -> str:
        cursor = self._cursor()
        cursor.execute(self.start_run_sql(), (self._require_source_id(), snapshot_hash, "{}"))
        run_id = str(cursor.fetchone()[0])
        self._fail("after_sync_run")
        return run_id

    def append_history(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None:
        inserted = False
        for command in plan_state_commands(plan):
            change_type = history_change_type(command.operation)
            if change_type is None:
                continue
            version = self._next_version(command.operation, command.record.key_hash)
            tombstone = command.operation is RawStateOperation.TOMBSTONE
            self._cursor().execute(
                self.append_raw_row_sql(),
                (
                    self._require_source_id(),
                    run_id,
                    None if tombstone else command.record.source_row_number,
                    command.record.key_hash,
                    None if tombstone else command.record.content_hash,
                    None if tombstone else json.dumps(command.record.values),
                    change_type,
                    version,
                ),
            )
            if not inserted:
                inserted = True
                self._fail("after_event")

    def commit(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None:
        changed = False
        for command in plan_state_commands(plan):
            cursor = self._cursor()
            record = command.record
            if command.operation is RawStateOperation.INSERT:
                parameters = (self._require_source_id(), record.key_hash, record.content_hash, json.dumps(record.values), record.source_row_number, run_id)
            elif command.operation is RawStateOperation.UPDATE:
                parameters = (record.content_hash, json.dumps(record.values), record.source_row_number, run_id, self._require_source_id(), record.key_hash)
            elif command.operation is RawStateOperation.TOMBSTONE:
                parameters = (run_id, self._require_source_id(), record.key_hash)
            elif command.operation is RawStateOperation.RESTORE:
                parameters = (record.content_hash, json.dumps(record.values), record.source_row_number, run_id, self._require_source_id(), record.key_hash)
            else:
                parameters = (record.source_row_number, run_id, self._require_source_id(), record.key_hash)
            cursor.execute(self.state_command_sql(command.operation), parameters)
            returned = cursor.fetchone()
            if returned is None:
                raise SyncError(ErrorCode.DATABASE, "Transicao raw nao afetou o estado esperado")
            self._versions[record.key_hash] = returned[0]
            if not changed:
                changed = True
                self._fail("after_state")

    def finish_run(self, run_id: str) -> None:
        counts = getattr(self, "_active_counts", None)
        if counts is None:
            raise SyncError(ErrorCode.INTERNAL, "Contagens da execucao nao configuradas")
        self._cursor().execute(
            self.finish_run_sql(),
            ("applied", counts["new"], counts["changed"], counts["removed"], counts["restored"], counts["unchanged"], run_id),
        )

    def set_active_plan(self, plan: RawChangePlan) -> None:
        self._active_counts = plan.counts

    def complete(self) -> None:
        self._fail("before_commit")
        self._require_connection().commit()

    def rollback(self, source_hash: str, run_id: str | None) -> None:
        if self._connection is not None:
            self._connection.rollback()

    def _cursor(self):
        return self._require_connection().cursor()

    def _require_connection(self) -> psycopg.Connection:
        if self._connection is None:
            raise SyncError(ErrorCode.DATABASE, "Transacao PostgreSQL nao iniciada")
        return self._connection

    def _require_source_id(self) -> str:
        if self._data_source_id is None:
            raise SyncError(ErrorCode.DATABASE, "Fonte PostgreSQL nao preparada")
        return self._data_source_id

    def _next_version(self, operation: RawStateOperation, key_hash: str) -> int:
        if operation is RawStateOperation.INSERT:
            return 1
        return self._versions[key_hash] + 1

    def _fail(self, point: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(point)

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
            "SELECT row_key_hash, content_hash, source_row_number, is_deleted, version, payload_json "
            "FROM public.raw_current_rows WHERE data_source_id = %s"
        )

    @staticmethod
    def insert_current_row_sql() -> str:
        return (
            "INSERT INTO public.raw_current_rows "
            "(data_source_id, row_key_hash, content_hash, payload_json, source_row_number, last_sync_run_id) "
            "VALUES (%s, %s, %s, %s::jsonb, %s, %s) RETURNING version"
        )

    @staticmethod
    def update_current_row_sql() -> str:
        return (
            "UPDATE public.raw_current_rows SET content_hash = %s, payload_json = %s::jsonb, "
            "source_row_number = %s, version = version + 1, last_seen_at = now(), updated_at = now(), "
            "last_sync_run_id = %s "
            "WHERE data_source_id = %s AND row_key_hash = %s AND NOT is_deleted RETURNING version"
        )

    @staticmethod
    def tombstone_current_row_sql() -> str:
        return (
            "UPDATE public.raw_current_rows SET is_deleted = true, deleted_at = now(), "
            "version = version + 1, updated_at = now(), last_sync_run_id = %s "
            "WHERE data_source_id = %s AND row_key_hash = %s AND NOT is_deleted RETURNING version"
        )

    @staticmethod
    def restore_current_row_sql() -> str:
        return (
            "UPDATE public.raw_current_rows SET is_deleted = false, deleted_at = NULL, "
            "content_hash = %s, payload_json = %s::jsonb, source_row_number = %s, "
            "version = version + 1, last_seen_at = now(), updated_at = now(), last_sync_run_id = %s "
            "WHERE data_source_id = %s AND row_key_hash = %s AND is_deleted RETURNING version"
        )

    @staticmethod
    def touch_current_row_sql() -> str:
        return (
            "UPDATE public.raw_current_rows SET last_seen_at = now(), source_row_number = %s, "
            "last_sync_run_id = %s "
            "WHERE data_source_id = %s AND row_key_hash = %s AND NOT is_deleted RETURNING version"
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
