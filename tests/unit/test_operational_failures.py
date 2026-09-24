from __future__ import annotations

import logging
import unittest
from datetime import UTC, datetime

from sheets_supabase_sync.errors import ErrorCode, SyncError
from sheets_supabase_sync.operational_failures import (
    DatabaseStage,
    FailureDisposition,
    busy_decision,
    classify_postgres_failure,
)
from sheets_supabase_sync.raw_repository import (
    InMemoryRawStateRepository,
    PostgresRawRepository,
    RawSchemaAssessment,
    ReconciliationOutcome,
)
from sheets_supabase_sync.raw_sync import RawInputRow, RawSyncSource, build_raw_snapshot, compare_raw_snapshots
from sheets_supabase_sync.raw_sync_service import RawSynchronizationService
from sheets_supabase_sync.retries import RetryPolicy
from sheets_supabase_sync.postgres_retry import connect_with_retry


NOW = datetime(2026, 8, 19, tzinfo=UTC)
SOURCE_HASH = "safe-source-hash"
SOURCE = RawSyncSource("fixture", SOURCE_HASH, "fixture", "Fixture", "fixture_raw", ("id",))
HEADER = ("id", "value")


class DriverError(Exception):
    def __init__(self, sqlstate: str) -> None:
        self.sqlstate = sqlstate


class ScriptedCursor:
    def __init__(self, connection) -> None:
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def execute(self, statement, parameters=()) -> None:
        self.connection.executed.append((statement, parameters))

    def fetchall(self):
        return self.connection.fetchall_results.pop(0)

    def fetchone(self):
        return self.connection.fetchone_results.pop(0)


class ScriptedConnection:
    def __init__(self, *, fetchall_results=(), fetchone_results=(), commit_error=None) -> None:
        self.fetchall_results = list(fetchall_results)
        self.fetchone_results = list(fetchone_results)
        self.commit_error = commit_error
        self.executed = []
        self.rollback_calls = 0
        self.closed = False

    def cursor(self):
        return ScriptedCursor(self)

    def commit(self) -> None:
        if self.commit_error:
            raise self.commit_error

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.closed = True


def rows(value: str = "one") -> tuple[RawInputRow, ...]:
    return (RawInputRow(2, {"id": "a", "value": value}),)


def service(repository: InMemoryRawStateRepository, *, logger: logging.Logger | None = None) -> RawSynchronizationService:
    return RawSynchronizationService(
        repository,
        logger,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.1, max_delay_seconds=1, max_elapsed_seconds=5, jitter_ratio=0),
        pause=lambda _: None,
        random_value=lambda: 0,
        execution_id_factory=lambda: "11111111-1111-4111-8111-111111111111",
    )


class PostgresFailurePolicyTests(unittest.TestCase):
    def test_connection_failures_are_retryable_before_commit(self) -> None:
        for stage in (DatabaseStage.CONNECT, DatabaseStage.TRANSACTION, DatabaseStage.BEFORE_COMMIT):
            with self.subTest(stage=stage):
                decision = classify_postgres_failure(DriverError("08006"), stage)
                self.assertEqual(FailureDisposition.RETRYABLE, decision.disposition)

    def test_connection_loss_during_commit_is_ambiguous(self) -> None:
        decision = classify_postgres_failure(DriverError("08006"), DatabaseStage.COMMIT)
        self.assertEqual(FailureDisposition.AMBIGUOUS_OUTCOME, decision.disposition)
        self.assertFalse(decision.retryable)

    def test_serialization_and_deadlock_are_retryable(self) -> None:
        for sqlstate in ("40001", "40P01"):
            with self.subTest(sqlstate=sqlstate):
                self.assertTrue(classify_postgres_failure(DriverError(sqlstate), DatabaseStage.TRANSACTION).retryable)

    def test_authentication_configuration_and_unknown_are_not_retryable(self) -> None:
        for error in (DriverError("28P01"), DriverError("3D000"), DriverError("42P01"), RuntimeError("opaque")):
            with self.subTest(error=type(error).__name__, sqlstate=getattr(error, "sqlstate", None)):
                self.assertEqual(
                    FailureDisposition.NON_RETRYABLE,
                    classify_postgres_failure(error, DatabaseStage.CONNECT).disposition,
                )

    def test_dns_tcp_and_timeout_are_retryable_only_outside_commit(self) -> None:
        for error in (TimeoutError(), ConnectionError(), OSError()):
            self.assertTrue(classify_postgres_failure(error, DatabaseStage.CONNECT).retryable)
            self.assertEqual(
                FailureDisposition.AMBIGUOUS_OUTCOME,
                classify_postgres_failure(error, DatabaseStage.COMMIT).disposition,
            )

    def test_busy_is_a_distinct_deferred_outcome(self) -> None:
        self.assertEqual(FailureDisposition.BUSY_DEFERRED, busy_decision().disposition)


class TransactionRetryTests(unittest.TestCase):
    def test_rollback_then_retry_reloads_state_and_reuses_execution_identity(self) -> None:
        transient = SyncError(ErrorCode.DATABASE_TRANSIENT, "temporary", True)
        repository = InMemoryRawStateRepository(faults={"state": [transient]})
        result = service(repository).persist_locally(SOURCE, HEADER, rows(), NOW)
        self.assertTrue(result.persisted)
        self.assertEqual(2, repository._lock_attempts)
        self.assertEqual(2, repository._snapshot_loads)
        self.assertEqual(2, repository._started_execution_ids.count("11111111-1111-4111-8111-111111111111"))
        self.assertEqual(1, len(repository.current_rows(SOURCE_HASH)))
        self.assertEqual(1, len(repository.history()))
        self.assertEqual(1, next(iter(repository.current_rows(SOURCE_HASH).values())).version)

    def test_retry_of_update_creates_one_event_and_one_version(self) -> None:
        repository = InMemoryRawStateRepository()
        service(repository).persist_locally(SOURCE, HEADER, rows(), NOW)
        repository._faults["state"] = [SyncError(ErrorCode.DATABASE_TRANSIENT, "temporary", True)]
        service(repository).persist_locally(SOURCE, HEADER, rows("changed"), NOW)
        self.assertEqual(2, len(repository.history()))
        self.assertEqual(2, next(iter(repository.current_rows(SOURCE_HASH).values())).version)

    def test_retry_exhaustion_preserves_previous_state(self) -> None:
        repository = InMemoryRawStateRepository()
        service(repository).persist_locally(SOURCE, HEADER, rows(), NOW)
        repository._faults["state"] = [
            SyncError(ErrorCode.DATABASE_TRANSIENT, "temporary", True),
            SyncError(ErrorCode.DATABASE_TRANSIENT, "temporary", True),
            SyncError(ErrorCode.DATABASE_TRANSIENT, "temporary", True),
        ]
        with self.assertRaises(SyncError) as raised:
            service(repository).persist_locally(SOURCE, HEADER, rows("changed"), NOW)
        self.assertEqual(ErrorCode.DATABASE_TRANSIENT, raised.exception.code)
        self.assertEqual(1, len(repository.history()))
        self.assertEqual(1, next(iter(repository.current_rows(SOURCE_HASH).values())).version)

    def test_confirmed_failure_before_commit_can_retry_safely(self) -> None:
        repository = InMemoryRawStateRepository(faults={"before_commit": [SyncError(ErrorCode.DATABASE_TRANSIENT, "temporary", True)]})
        service(repository).persist_locally(SOURCE, HEADER, rows(), NOW)
        self.assertEqual(1, len(repository.history()))
        self.assertEqual(1, next(iter(repository.current_rows(SOURCE_HASH).values())).version)

    def test_ambiguous_commit_already_persisted_is_reconciled_without_retry(self) -> None:
        repository = InMemoryRawStateRepository(lose_commit_ack=True)
        result = service(repository).persist_locally(SOURCE, HEADER, rows(), NOW)
        self.assertEqual(ReconciliationOutcome.APPLIED, result.reconciliation)
        self.assertEqual(1, len(repository._started_execution_ids))
        self.assertEqual(1, repository._reconciliation_calls)
        self.assertEqual(1, len(repository.history()))
        self.assertEqual("applied", repository.run_status("11111111-1111-4111-8111-111111111111"))

    def test_ambiguous_commit_not_persisted_retries_full_transaction(self) -> None:
        repository = InMemoryRawStateRepository(
            ambiguous_reconciliations=(ReconciliationOutcome.NOT_PERSISTED,),
        )
        result = service(repository).persist_locally(SOURCE, HEADER, rows(), NOW)
        self.assertTrue(result.persisted)
        self.assertEqual("not_required", result.reconciliation)
        self.assertEqual(2, repository._snapshot_loads)
        self.assertEqual(2, len(repository._started_execution_ids))
        self.assertEqual(1, len(repository.history()))

    def test_ambiguous_commit_inconclusive_fails_closed_without_retry(self) -> None:
        repository = InMemoryRawStateRepository(
            ambiguous_reconciliations=(ReconciliationOutcome.INCONCLUSIVE,),
        )
        with self.assertRaises(SyncError) as raised:
            service(repository).persist_locally(SOURCE, HEADER, rows(), NOW)
        self.assertEqual(ErrorCode.AMBIGUOUS_OUTCOME, raised.exception.code)
        self.assertEqual(1, len(repository._started_execution_ids))
        self.assertEqual(1, repository._reconciliation_calls)

    def test_non_retryable_transaction_error_is_not_retried(self) -> None:
        repository = InMemoryRawStateRepository(
            faults={"state": [SyncError(ErrorCode.DATABASE, "permanent", False)]},
        )
        with self.assertRaises(SyncError) as raised:
            service(repository).persist_locally(SOURCE, HEADER, rows(), NOW)
        self.assertEqual(ErrorCode.DATABASE, raised.exception.code)
        self.assertEqual(1, repository._lock_attempts)
        self.assertEqual(1, len(repository._started_execution_ids))

    def test_busy_does_not_create_a_run_or_retry(self) -> None:
        repository = InMemoryRawStateRepository()
        repository.try_acquire(SOURCE_HASH)
        logger = logging.getLogger("test.raw.busy")
        with self.assertLogs(logger, "INFO") as captured:
            with self.assertRaises(SyncError) as raised:
                service(repository, logger=logger).persist_locally(SOURCE, HEADER, rows(), NOW)
        self.assertEqual(ErrorCode.BUSY, raised.exception.code)
        self.assertEqual([], repository._started_execution_ids)
        self.assertIn('"outcome": "busy_deferred"', captured.output[0])

    def test_retry_logs_are_sanitized_and_complete(self) -> None:
        logger = logging.getLogger("test.raw.operational")
        repository = InMemoryRawStateRepository(
            faults={"state": [SyncError(ErrorCode.DATABASE_TRANSIENT, "password=secret", True)]}
        )
        with self.assertLogs(logger, "INFO") as captured:
            service(repository, logger=logger).persist_locally(SOURCE, HEADER, rows("private-cell"), NOW)
        retry_line = next(line for line in captured.output if "raw_sync_retry" in line)
        for field in ("operation", "attempt", "max_attempts", "error_category", "retryable", "backoff_ms", "duration_ms", "outcome"):
            self.assertIn(field, retry_line)
        self.assertNotIn("private-cell", " ".join(captured.output))
        self.assertNotIn("password=secret", " ".join(captured.output))

    def test_existing_run_id_can_be_reconciled_without_schema_change(self) -> None:
        statement = PostgresRawRepository.reconcile_run_sql()
        self.assertIn("WHERE id = %s AND data_source_id = %s", statement)
        self.assertIn("snapshot_hash", statement)


class PostgresReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = compare_raw_snapshots(build_raw_snapshot(SOURCE, HEADER, rows(), NOW), None)
        self.source_row = ("source-id", "fixture", "fixture", "Fixture", "fixture_raw", ["id"], True)

    def repository(self, connection: ScriptedConnection) -> PostgresRawRepository:
        return PostgresRawRepository(
            RawSchemaAssessment(True, ()),
            "postgresql://redacted@host/postgres",
            connection_factory=lambda _: connection,
        )

    def test_postgres_preview_is_read_only_unlocked_and_write_free(self) -> None:
        connection = ScriptedConnection(fetchall_results=([self.source_row], []))
        snapshot = self.repository(connection).preview_snapshot(SOURCE, HEADER, NOW)
        self.assertIsNone(snapshot)
        statements = [statement.upper() for statement, _ in connection.executed]
        self.assertEqual("SET TRANSACTION READ ONLY", statements[0])
        self.assertNotIn("FOR SHARE", " ".join(statements))
        self.assertNotIn("FOR UPDATE", " ".join(statements))
        self.assertTrue(all(statement.startswith(("SELECT", "SET TRANSACTION READ ONLY")) for statement in statements))

    def test_postgres_write_source_lookup_keeps_share_lock(self) -> None:
        connection = ScriptedConnection(fetchall_results=([self.source_row],))
        repository = self.repository(connection)
        repository._connection = connection
        repository.prepare_source(SOURCE)
        self.assertIn("FOR SHARE", connection.executed[0][0].upper())

    def test_postgres_reconciliation_confirms_applied_run_events_and_state(self) -> None:
        connection = ScriptedConnection(
            fetchall_results=([self.source_row],),
            fetchone_results=(("applied", self.plan.snapshot.snapshot_hash, 1, 0, 0, 0, 0), (1,), (1,)),
        )
        outcome = self.repository(connection).reconcile_run(SOURCE, "run-id", self.plan)
        self.assertEqual(ReconciliationOutcome.APPLIED, outcome)
        statements = " ".join(statement for statement, _ in connection.executed)
        self.assertIn("SET TRANSACTION READ ONLY", statements)
        self.assertNotIn("FOR SHARE", statements.upper())
        self.assertNotIn("FOR UPDATE", statements.upper())
        self.assertIn("raw_import_rows", statements)
        self.assertIn("raw_current_rows", statements)

    def test_postgres_reconciliation_identifies_absent_run_as_not_persisted(self) -> None:
        connection = ScriptedConnection(fetchall_results=([self.source_row],), fetchone_results=(None,))
        self.assertEqual(ReconciliationOutcome.NOT_PERSISTED, self.repository(connection).reconcile_run(SOURCE, "run-id", self.plan))

    def test_postgres_reconciliation_fails_closed_on_divergent_run(self) -> None:
        connection = ScriptedConnection(
            fetchall_results=([self.source_row],),
            fetchone_results=(("running", self.plan.snapshot.snapshot_hash, 0, 0, 0, 0, 0),),
        )
        self.assertEqual(ReconciliationOutcome.INCONCLUSIVE, self.repository(connection).reconcile_run(SOURCE, "run-id", self.plan))

    def test_postgres_commit_connection_loss_is_exposed_as_ambiguous(self) -> None:
        connection = ScriptedConnection(commit_error=DriverError("08006"))
        repository = self.repository(connection)
        repository._connection = connection
        with self.assertRaises(SyncError) as raised:
            repository.commit_transaction(SOURCE_HASH, "run-id")
        self.assertEqual(ErrorCode.AMBIGUOUS_OUTCOME, raised.exception.code)


class ConnectionRetryTests(unittest.TestCase):
    def test_transient_connection_failure_then_success(self) -> None:
        attempts = 0
        pauses: list[float] = []

        def connect():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise DriverError("08006")
            return "connection"

        result = connect_with_retry(
            connect,
            source_prefix=SOURCE_HASH,
            policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.1, max_delay_seconds=1, max_elapsed_seconds=5, jitter_ratio=0),
            pause=pauses.append,
            random_value=lambda: 0,
        )
        self.assertEqual("connection", result)
        self.assertEqual(2, attempts)
        self.assertEqual([0.1], pauses)

    def test_authentication_failure_never_retries(self) -> None:
        attempts = 0

        def connect():
            nonlocal attempts
            attempts += 1
            raise DriverError("28P01")

        with self.assertRaises(SyncError) as raised:
            connect_with_retry(connect, source_prefix=SOURCE_HASH, pause=lambda _: None)
        self.assertEqual(ErrorCode.DATABASE, raised.exception.code)
        self.assertEqual(1, attempts)

    def test_connection_retry_exhaustion_is_bounded(self) -> None:
        attempts = 0

        def connect():
            nonlocal attempts
            attempts += 1
            raise TimeoutError()

        with self.assertRaises(SyncError) as raised:
            connect_with_retry(
                connect,
                source_prefix=SOURCE_HASH,
                policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.1, max_delay_seconds=1, max_elapsed_seconds=5, jitter_ratio=0),
                pause=lambda _: None,
                random_value=lambda: 0,
            )
        self.assertEqual(ErrorCode.DATABASE_TRANSIENT, raised.exception.code)
        self.assertEqual(3, attempts)


if __name__ == "__main__":
    unittest.main()
