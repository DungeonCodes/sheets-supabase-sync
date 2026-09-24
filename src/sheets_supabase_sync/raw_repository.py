from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Callable, Mapping, Protocol, Sequence, TypeVar

import psycopg

from .errors import ErrorCode, SyncError
from .operational_failures import DatabaseStage, postgres_sync_error
from .postgres_retry import connect_with_retry
from .raw_state import RawCurrentRow, RawStateOperation, apply_state_command, history_change_type, plan_state_commands
from .raw_schema import RawSchema, RawSchemaChange
from .raw_sync import RawChangePlan, RawRecord, RawSnapshot, RawSyncSource, compute_snapshot_hash


ResultT = TypeVar("ResultT")


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


class ReconciliationOutcome(StrEnum):
    APPLIED = "applied"
    NOT_PERSISTED = "not_persisted"
    INCONCLUSIVE = "inconclusive"


class _PostgresTransactionCursor:
    """Converte falhas do driver em erros do dominio no escopo transacional."""

    def __init__(self, cursor: psycopg.Cursor) -> None:
        self._cursor = cursor

    def execute(self, *args, **kwargs):
        return self._operation(lambda: self._cursor.execute(*args, **kwargs))

    def fetchone(self):
        return self._operation(self._cursor.fetchone)

    def fetchall(self):
        return self._operation(self._cursor.fetchall)

    def _operation(self, operation: Callable[[], ResultT]) -> ResultT:
        try:
            return operation()
        except SyncError:
            raise
        except Exception as error:
            raise postgres_sync_error(error, DatabaseStage.TRANSACTION) from error


class RawStateRepository(Protocol):
    def try_acquire(self, source_hash: str) -> bool: ...

    def release(self, source_hash: str) -> None: ...

    def prepare_source(self, source: RawSyncSource) -> None: ...

    def preview_snapshot(
        self,
        source: RawSyncSource,
        header: tuple[str, ...],
        read_at: datetime,
    ) -> RawSnapshot | None: ...

    def load_schema(self, source_hash: str) -> RawSchema | None: ...

    def record_schema_change(self, change: RawSchemaChange) -> None: ...

    def load_snapshot(
        self,
        source_hash: str,
        header: tuple[str, ...] = (),
        read_at: datetime | None = None,
    ) -> RawSnapshot | None: ...

    def start_run(self, source_hash: str, snapshot_hash: str, execution_id: str) -> str: ...

    def append_history(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None: ...

    def apply_plan(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None: ...

    def finish_run(self, run_id: str) -> None: ...

    def set_active_plan(self, plan: RawChangePlan) -> None: ...

    def commit_transaction(self, source_hash: str, run_id: str) -> None: ...

    def reconcile_run(
        self,
        source: RawSyncSource,
        execution_id: str,
        plan: RawChangePlan,
    ) -> ReconciliationOutcome: ...

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
    runs: Mapping[str, str]
    registered_sources: Mapping[str, tuple[RawSyncSource, bool]]


class InMemoryRawStateRepository:
    """Referencia local da semantica transacional; nao abre conexao PostgreSQL."""

    def __init__(
        self,
        fail_on_start: bool = False,
        fail_on_history: bool = False,
        fail_on_commit: bool = False,
        fail_on_finish: bool = False,
        fail_before_transaction_commit: bool = False,
        lose_commit_ack: bool = False,
        faults: Mapping[str, Sequence[SyncError]] | None = None,
        existing_sources: Sequence[tuple[RawSyncSource, bool]] = (),
        ambiguous_reconciliations: Sequence[ReconciliationOutcome] = (),
    ) -> None:
        self._sources: dict[str, _StoredSource] = {}
        self._checkpoints: dict[str, _Checkpoint] = {}
        self._history: list[RawHistoryEntry] = []
        self._schema_changes: list[RawSchemaChange] = []
        self._locks: set[str] = set()
        self._runs: dict[str, str] = {}
        self._next_run = 1
        self._started_execution_ids: list[str] = []
        self._snapshot_loads = 0
        self._lock_attempts = 0
        self._source_writes = 0
        self._registered_sources = {source.logical_name: (source, enabled) for source, enabled in existing_sources}
        self._ambiguous_reconciliations = list(ambiguous_reconciliations)
        if lose_commit_ack:
            self._ambiguous_reconciliations.insert(0, ReconciliationOutcome.APPLIED)
        self._pending_reconciliation: ReconciliationOutcome | None = None
        self._reconciliation_calls = 0
        self._fail_on_start = fail_on_start
        self._fail_on_history = fail_on_history
        self._fail_on_commit = fail_on_commit
        self._fail_on_finish = fail_on_finish
        self._fail_before_transaction_commit = fail_before_transaction_commit
        self._faults = {stage: list(errors) for stage, errors in (faults or {}).items()}

    def try_acquire(self, source_hash: str) -> bool:
        self._lock_attempts += 1
        if source_hash in self._locks:
            return False
        self._locks.add(source_hash)
        return True

    def release(self, source_hash: str) -> None:
        self._locks.discard(source_hash)

    def prepare_source(self, source: RawSyncSource) -> None:
        matches = self._matching_sources(source)
        if matches:
            _validate_registered_source(source, matches)
            return
        self._ensure_checkpoint(source.source_hash)
        self._registered_sources[source.logical_name] = (source, True)
        self._source_writes += 1

    def preview_snapshot(
        self,
        source: RawSyncSource,
        header: tuple[str, ...],
        read_at: datetime,
    ) -> RawSnapshot | None:
        matches = self._matching_sources(source)
        if not matches:
            return None
        _validate_registered_source(source, matches)
        return self.load_snapshot(source.source_hash, header, read_at)

    def load_schema(self, source_hash: str) -> RawSchema | None:
        stored = self._sources.get(source_hash)
        return RawSchema.from_header(stored.header) if stored else None

    def record_schema_change(self, change: RawSchemaChange) -> None:
        if change not in self._schema_changes:
            self._schema_changes.append(change)

    def schema_changes(self) -> tuple[RawSchemaChange, ...]:
        return tuple(self._schema_changes)

    def load_snapshot(
        self,
        source_hash: str,
        header: tuple[str, ...] = (),
        read_at: datetime | None = None,
    ) -> RawSnapshot | None:
        self._snapshot_loads += 1
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

    def start_run(self, source_hash: str, snapshot_hash: str, execution_id: str) -> str:
        self._ensure_checkpoint(source_hash)
        self._inject("start")
        if self._fail_on_start:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada ao iniciar execucao")
        self._next_run += 1
        self._started_execution_ids.append(execution_id)
        self._runs[execution_id] = "running"
        return execution_id

    def append_history(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None:
        self._inject("history")
        if self._fail_on_history:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada ao registrar historico")
        for command in plan_state_commands(plan):
            change_type = history_change_type(command.operation)
            if change_type is not None:
                self._history.append(RawHistoryEntry(run_id, command.record.key_hash, change_type, command.record.source_row_number))

    def apply_plan(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None:
        self._inject("state")
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
        self._inject("finish")
        if self._fail_on_finish:
            raise SyncError(ErrorCode.DATABASE, "Falha local simulada ao finalizar execucao")
        self._runs[run_id] = "applied"

    def set_active_plan(self, plan: RawChangePlan) -> None:
        return None

    def commit_transaction(self, source_hash: str, run_id: str) -> None:
        self._inject("before_commit")
        if self._fail_before_transaction_commit:
            raise SyncError(ErrorCode.DATABASE_TRANSIENT, "Falha transitoria antes do commit", True)
        if self._ambiguous_reconciliations:
            outcome = self._ambiguous_reconciliations.pop(0)
            self._pending_reconciliation = outcome
            if outcome is ReconciliationOutcome.NOT_PERSISTED:
                self.rollback(source_hash, run_id)
            else:
                self._checkpoints.pop(source_hash, None)
            raise SyncError(ErrorCode.AMBIGUOUS_OUTCOME, "Resultado do commit desconhecido")
        self._checkpoints.pop(source_hash, None)

    def reconcile_run(
        self,
        source: RawSyncSource,
        execution_id: str,
        plan: RawChangePlan,
    ) -> ReconciliationOutcome:
        self._reconciliation_calls += 1
        if self._pending_reconciliation is not None:
            outcome = self._pending_reconciliation
            self._pending_reconciliation = None
            return outcome
        return ReconciliationOutcome.APPLIED if self._runs.get(execution_id) == "applied" else ReconciliationOutcome.NOT_PERSISTED

    def rollback(self, source_hash: str, run_id: str | None) -> None:
        checkpoint = self._checkpoints.pop(source_hash, None)
        if checkpoint is None:
            return
        if checkpoint.source is None:
            self._sources.pop(source_hash, None)
        else:
            self._sources[source_hash] = checkpoint.source
        del self._history[checkpoint.history_length :]
        self._runs = dict(checkpoint.runs)
        self._registered_sources = dict(checkpoint.registered_sources)

    def _matching_sources(self, source: RawSyncSource) -> list[tuple[RawSyncSource, bool]]:
        return [
            registered
            for registered in self._registered_sources.values()
            if registered[0].logical_name == source.logical_name
            or registered[0].target_table == source.target_table
            or (registered[0].spreadsheet_id, registered[0].sheet_name) == (source.spreadsheet_id, source.sheet_name)
        ]

    def _ensure_checkpoint(self, source_hash: str) -> None:
        if source_hash not in self._checkpoints:
            self._checkpoints[source_hash] = _Checkpoint(
                deepcopy(self._sources.get(source_hash)),
                len(self._history),
                dict(self._runs),
                dict(self._registered_sources),
            )

    def _inject(self, stage: str) -> None:
        scheduled = self._faults.get(stage)
        if scheduled:
            raise scheduled.pop(0)


class PostgresRawRepository:
    """Unidade transacional PostgreSQL para estado raw e eventos."""

    def __init__(
        self,
        assessment: RawSchemaAssessment,
        database_url: str | None = None,
        failure_injector: Callable[[str], None] | None = None,
        connection_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self._assessment = assessment
        self._database_url = database_url
        self._failure_injector = failure_injector
        self._connection_factory = connection_factory or (lambda url: psycopg.connect(url, autocommit=False))
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
        self._connection = connect_with_retry(
            lambda: self._connection_factory(self._database_url or ""),
            source_prefix=source_hash,
        )
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(self.try_lock_sql(), (source_hash,))
                acquired = bool(cursor.fetchone()[0])
        except Exception as error:
            self.rollback(source_hash, None)
            self.release(source_hash)
            raise _classify_database_error(error, DatabaseStage.TRANSACTION) from error
        if not acquired:
            self._connection.rollback()
            self.release(source_hash)
        return acquired

    def release(self, source_hash: str) -> None:
        connection = self._connection
        self._connection = None
        self._data_source_id = None
        self._versions = {}
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    def prepare_source(self, source: RawSyncSource) -> None:
        cursor = self._cursor()
        matches = self._find_sources(cursor, source)
        if matches:
            source_id = _validate_registered_source(source, matches)
            self._data_source_id = str(source_id)
            return
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
        returned = cursor.fetchone()
        if returned is None:
            raise SyncError(ErrorCode.SOURCE_MISMATCH, "Fonte nao pode ser cadastrada com a configuracao solicitada")
        data_source_id, lifecycle_status, enabled = returned
        if lifecycle_status != "active" or enabled is not True:
            raise SyncError(ErrorCode.SOURCE_INACTIVE, "Fonte PostgreSQL nao esta ativa para sincronizacao")
        self._data_source_id = str(data_source_id)

    def preview_snapshot(
        self,
        source: RawSyncSource,
        header: tuple[str, ...],
        read_at: datetime,
    ) -> RawSnapshot | None:
        self.assert_supported()
        if not self._database_url:
            raise SyncError(ErrorCode.CONFIGURATION, "URL PostgreSQL explicita obrigatoria")
        self._connection = connect_with_retry(
            lambda: self._connection_factory(self._database_url or ""),
            source_prefix=source.source_hash,
        )
        try:
            self._cursor().execute(self.read_only_transaction_sql())
            matches = self._find_sources(self._cursor(), source, lock=False)
            if not matches:
                return None
            self._data_source_id = str(_validate_registered_source(source, matches))
            return self.load_snapshot(source.source_hash, header, read_at)
        except SyncError:
            raise
        except Exception as error:
            raise _classify_database_error(error, DatabaseStage.TRANSACTION) from error
        finally:
            self.rollback(source.source_hash, None)
            self.release(source.source_hash)

    def load_schema(self, source_hash: str) -> RawSchema | None:
        cursor = self._cursor()
        cursor.execute(self.load_current_state_sql(), (self._require_source_id(),))
        rows = cursor.fetchall()
        if not rows:
            return None
        headers = {tuple(sorted((payload or {}).keys())) for _, _, _, _, _, payload in rows}
        if len(headers) != 1:
            raise SyncError(ErrorCode.SCHEMA, "Estado raw nao possui schema baseline consistente")
        return RawSchema(next(iter(headers)))

    def record_schema_change(self, change: RawSchemaChange) -> None:
        self._cursor().execute(
            self.record_schema_change_sql(),
            (
                self._require_source_id(), change.change_type, json.dumps(change.previous.as_json()), json.dumps(change.proposed.as_json()),
                self._require_source_id(), change.change_type, json.dumps(change.previous.as_json()), json.dumps(change.proposed.as_json()),
            ),
        )

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

    def start_run(self, source_hash: str, snapshot_hash: str, execution_id: str) -> str:
        cursor = self._cursor()
        cursor.execute(self.start_run_sql(), (execution_id, self._require_source_id(), snapshot_hash, "{}"))
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

    def apply_plan(self, source_hash: str, run_id: str, plan: RawChangePlan) -> None:
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

    def commit_transaction(self, source_hash: str, run_id: str) -> None:
        self._fail("before_commit")
        try:
            self._require_connection().commit()
            self._fail("after_commit")
        except Exception as error:
            raise _classify_database_error(error, DatabaseStage.COMMIT) from error

    def reconcile_run(
        self,
        source: RawSyncSource,
        execution_id: str,
        plan: RawChangePlan,
    ) -> ReconciliationOutcome:
        if not self._database_url:
            return ReconciliationOutcome.INCONCLUSIVE
        try:
            self._connection = connect_with_retry(
                lambda: self._connection_factory(self._database_url or ""),
                source_prefix=source.source_hash,
            )
            self._cursor().execute(self.read_only_transaction_sql())
            matches = self._find_sources(self._cursor(), source, lock=False)
            if not matches:
                return ReconciliationOutcome.NOT_PERSISTED
            self._data_source_id = str(_validate_registered_source(source, matches, require_active=False))
            cursor = self._cursor()
            cursor.execute(self.reconcile_run_sql(), (execution_id, self._require_source_id()))
            run = cursor.fetchone()
            if run is None:
                return ReconciliationOutcome.NOT_PERSISTED
            expected_counts = plan.counts
            expected_run = (
                "applied",
                plan.snapshot.snapshot_hash,
                expected_counts["new"],
                expected_counts["changed"],
                expected_counts["removed"],
                expected_counts["restored"],
                expected_counts["unchanged"],
            )
            if tuple(run) != expected_run:
                return ReconciliationOutcome.INCONCLUSIVE
            cursor.execute(self.reconcile_event_count_sql(), (execution_id, self._require_source_id()))
            event_count = int(cursor.fetchone()[0])
            cursor.execute(self.reconcile_state_count_sql(), (execution_id, self._require_source_id()))
            state_count = int(cursor.fetchone()[0])
            expected_events = len(plan.new) + len(plan.changed) + len(plan.removed) + len(plan.restored)
            expected_state = sum(expected_counts.values())
            if (event_count, state_count) != (expected_events, expected_state):
                return ReconciliationOutcome.INCONCLUSIVE
            return ReconciliationOutcome.APPLIED
        except Exception:
            return ReconciliationOutcome.INCONCLUSIVE
        finally:
            self.rollback(source.source_hash, execution_id)
            self.release(source.source_hash)

    def complete(self) -> None:
        """Compatibilidade para testes de lock que nao iniciam uma sync."""
        self._require_connection().commit()

    def rollback(self, source_hash: str, run_id: str | None) -> None:
        if self._connection is not None:
            try:
                self._connection.rollback()
            except Exception:
                pass

    def _cursor(self):
        return _PostgresTransactionCursor(self._require_connection().cursor())

    def _transaction_operation(
        self,
        operation: Callable[[], ResultT],
        stage: DatabaseStage = DatabaseStage.TRANSACTION,
    ) -> ResultT:
        try:
            return operation()
        except SyncError:
            raise
        except Exception as error:
            raise postgres_sync_error(error, stage) from error

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

    def _find_sources(self, cursor: Any, source: RawSyncSource, *, lock: bool = True) -> list[tuple[Any, ...]]:
        cursor.execute(
            self.find_source_sql(lock=lock),
            (source.logical_name, source.target_table, source.spreadsheet_id, source.sheet_name),
        )
        return list(cursor.fetchall())

    @staticmethod
    def find_source_sql(*, lock: bool = True) -> str:
        statement = (
            "SELECT id, name, spreadsheet_id, sheet_name, target_table, business_key, lifecycle_status, enabled "
            "FROM public.data_sources WHERE name = %s OR target_table = %s "
            "OR (spreadsheet_id = %s AND sheet_name = %s)"
        )
        return f"{statement} FOR SHARE" if lock else statement

    @staticmethod
    def read_only_transaction_sql() -> str:
        return "SET TRANSACTION READ ONLY"

    @staticmethod
    def register_source_sql() -> str:
        return (
            "INSERT INTO public.data_sources (name, spreadsheet_id, sheet_name, target_table, business_key) "
            "VALUES (%s, %s, %s, %s, %s::jsonb) "
            "ON CONFLICT (spreadsheet_id, sheet_name) DO NOTHING "
            "RETURNING id, lifecycle_status, enabled"
        )

    @staticmethod
    def record_schema_change_sql() -> str:
        return (
            "INSERT INTO public.schema_change_requests (data_source_id, change_type, previous_schema, proposed_schema) "
            "SELECT %s, %s, %s::jsonb, %s::jsonb "
            "WHERE NOT EXISTS (SELECT 1 FROM public.schema_change_requests "
            "WHERE data_source_id = %s AND change_type = %s AND previous_schema = %s::jsonb "
            "AND proposed_schema = %s::jsonb AND status = 'pending')"
        )

    @staticmethod
    def start_run_sql() -> str:
        return (
            "INSERT INTO public.sync_runs "
            "(id, data_source_id, status, snapshot_hash, schema_metadata) "
            "VALUES (%s, %s, 'running', %s, %s::jsonb) RETURNING id"
        )

    @staticmethod
    def reconcile_run_sql() -> str:
        return (
            "SELECT status, snapshot_hash, inserted_rows, updated_rows, deleted_rows, restored_rows, unchanged_rows "
            "FROM public.sync_runs WHERE id = %s AND data_source_id = %s"
        )

    @staticmethod
    def reconcile_event_count_sql() -> str:
        return "SELECT count(*) FROM public.raw_import_rows WHERE sync_run_id = %s AND data_source_id = %s"

    @staticmethod
    def reconcile_state_count_sql() -> str:
        return "SELECT count(*) FROM public.raw_current_rows WHERE last_sync_run_id = %s AND data_source_id = %s"

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


def _validate_registered_source(
    requested: RawSyncSource,
    matches: Sequence[tuple[Any, ...] | tuple[RawSyncSource, bool]],
    *,
    require_active: bool = True,
) -> Any:
    if len(matches) != 1:
        raise SyncError(ErrorCode.SOURCE_MISMATCH, "Fonte existente possui identidade conflitante")
    item = matches[0]
    if len(item) == 2 and isinstance(item[0], RawSyncSource):
        stored, enabled = item
        source_id: Any = stored.logical_name
        lifecycle_status = "active" if enabled else "suspended"
    elif len(item) == 7:
        source_id, name, spreadsheet_id, sheet_name, target_table, business_key, enabled = item
        lifecycle_status = "active" if enabled else "suspended"
        stored = RawSyncSource(name, requested.source_hash, spreadsheet_id, sheet_name, target_table, tuple(business_key or ()))
    else:
        source_id, name, spreadsheet_id, sheet_name, target_table, business_key, lifecycle_status, enabled = item
        stored = RawSyncSource(name, requested.source_hash, spreadsheet_id, sheet_name, target_table, tuple(business_key or ()))
    expected = (
        requested.logical_name,
        requested.spreadsheet_id,
        requested.sheet_name,
        requested.target_table,
        requested.business_key,
    )
    actual = (stored.logical_name, stored.spreadsheet_id, stored.sheet_name, stored.target_table, stored.business_key)
    if actual != expected:
        raise SyncError(ErrorCode.SOURCE_MISMATCH, "Fonte existente diverge da configuracao solicitada")
    if require_active and (lifecycle_status != "active" or enabled is not True):
        raise SyncError(ErrorCode.SOURCE_INACTIVE, "Fonte existente nao esta ativa")
    return source_id


def _classify_database_error(error: BaseException, stage: DatabaseStage) -> SyncError:
    if isinstance(error, SyncError):
        return error
    return postgres_sync_error(error, stage)
