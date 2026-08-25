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
from sheets_supabase_sync.raw_repository import InMemoryRawStateRepository, PostgresRawRepository
from sheets_supabase_sync.raw_sync import RawInputRow, RawSyncSource
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

    def test_unknown_commit_is_preserved_and_never_retried(self) -> None:
        repository = InMemoryRawStateRepository(lose_commit_ack=True)
        with self.assertRaises(SyncError) as raised:
            service(repository).persist_locally(SOURCE, HEADER, rows(), NOW)
        self.assertEqual(ErrorCode.AMBIGUOUS_OUTCOME, raised.exception.code)
        self.assertEqual(1, len(repository._started_execution_ids))
        self.assertEqual(1, len(repository.history()))
        self.assertEqual("applied", repository.run_status("11111111-1111-4111-8111-111111111111"))

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
