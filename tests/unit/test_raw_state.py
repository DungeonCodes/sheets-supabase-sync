from __future__ import annotations

import logging
import unittest
from datetime import UTC, datetime

from sheets_supabase_sync.errors import ErrorCode, SyncError
from sheets_supabase_sync.raw_repository import InMemoryRawStateRepository, PostgresRawRepository
from sheets_supabase_sync.raw_state import RawStateOperation, plan_state_commands
from sheets_supabase_sync.raw_sync import RawInputRow, RawRecord, RawSyncSource, build_raw_snapshot, compare_raw_snapshots
from sheets_supabase_sync.raw_sync_service import RawSynchronizationService


NOW = datetime(2026, 8, 6, tzinfo=UTC)
HEADER = ("registro_id", "valor")
SOURCE_HASH = "source-hash"


def source() -> RawSyncSource:
    return RawSyncSource("fixture", SOURCE_HASH, "in-memory-only", "Fixture", "fixture_raw_future", ("registro_id",))


def rows(*items: tuple[int, str, str]) -> tuple[RawInputRow, ...]:
    return tuple(RawInputRow(number, {"registro_id": key, "valor": value}) for number, key, value in items)


def persist(repository: InMemoryRawStateRepository, *items: tuple[int, str, str]):
    return RawSynchronizationService(repository).persist_locally(source(), HEADER, rows(*items), NOW)


def only_row(repository: InMemoryRawStateRepository):
    current = repository.current_rows(SOURCE_HASH)
    return next(iter(current.values()))


class RawCurrentStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryRawStateRepository()

    def test_first_load_creates_active_row_at_version_one(self) -> None:
        persist(self.repository, (2, "a", "one"))
        row = only_row(self.repository)
        self.assertEqual(1, row.version)
        self.assertFalse(row.is_deleted)
        self.assertEqual(2, row.source_row_number)

    def test_identical_load_keeps_version_and_stays_unchanged(self) -> None:
        persist(self.repository, (2, "a", "one"))
        result = persist(self.repository, (2, "a", "one"))
        self.assertEqual(1, only_row(self.repository).version)
        self.assertEqual(1, result.plan.counts["unchanged"])
        self.assertEqual(0, result.metrics.rows_persisted)

    def test_content_change_increments_version_and_keeps_identity(self) -> None:
        persist(self.repository, (2, "a", "one"))
        first_key = only_row(self.repository).key_hash
        persist(self.repository, (2, "a", "two"))
        row = only_row(self.repository)
        self.assertEqual(2, row.version)
        self.assertEqual(first_key, row.key_hash)
        self.assertEqual(1, len(self.repository.current_rows(SOURCE_HASH)))

    def test_removal_marks_tombstone_without_dropping_the_row(self) -> None:
        persist(self.repository, (2, "a", "one"), (3, "b", "two"))
        persist(self.repository, (2, "a", "one"))
        tombstones = [row for row in self.repository.current_rows(SOURCE_HASH).values() if row.is_deleted]
        self.assertEqual(1, len(tombstones))
        self.assertEqual(2, tombstones[0].version)
        self.assertEqual(2, len(self.repository.current_rows(SOURCE_HASH)))

    def test_restoration_reuses_identity_and_clears_tombstone(self) -> None:
        persist(self.repository, (2, "a", "one"), (3, "b", "two"))
        persist(self.repository, (2, "a", "one"))
        deleted_key = next(key for key, row in self.repository.current_rows(SOURCE_HASH).items() if row.is_deleted)
        result = persist(self.repository, (2, "a", "one"), (3, "b", "two"))
        restored = self.repository.current_rows(SOURCE_HASH)[deleted_key]
        self.assertFalse(restored.is_deleted)
        self.assertEqual(3, restored.version)
        self.assertEqual(1, result.plan.counts["restored"])
        self.assertEqual(0, result.plan.counts["new"])

    def test_reordering_updates_row_number_without_content_or_version_change(self) -> None:
        persist(self.repository, (2, "a", "one"), (3, "b", "two"))
        before = dict(self.repository.current_rows(SOURCE_HASH))
        result = persist(self.repository, (2, "b", "two"), (3, "a", "one"))
        after = self.repository.current_rows(SOURCE_HASH)
        self.assertEqual(2, result.plan.counts["unchanged"])
        for key_hash, previous in before.items():
            self.assertEqual(previous.content_hash, after[key_hash].content_hash)
            self.assertEqual(previous.version, after[key_hash].version)
        self.assertNotEqual(
            [row.source_row_number for row in before.values()],
            [after[key].source_row_number for key in before],
        )

    def test_duplicate_identity_is_refused_by_the_state_transition(self) -> None:
        snapshot = build_raw_snapshot(source(), HEADER, rows((2, "a", "one")), NOW)
        plan = compare_raw_snapshots(snapshot, None)
        self.repository.commit(SOURCE_HASH, "run-manual", plan)
        with self.assertRaises(SyncError) as raised:
            self.repository.commit(SOURCE_HASH, "run-manual", plan)
        self.assertEqual(ErrorCode.VALIDATION, raised.exception.code)

    def test_history_records_only_business_events(self) -> None:
        persist(self.repository, (2, "a", "one"), (3, "b", "two"))
        persist(self.repository, (2, "a", "changed"))
        change_types = [entry.change_type for entry in self.repository.history()]
        self.assertEqual(["insert", "insert", "update", "tombstone"], change_types)
        self.assertNotIn("unchanged", change_types)


class RawStateFailureTests(unittest.TestCase):
    def test_history_failure_rolls_back_state_and_history(self) -> None:
        repository = InMemoryRawStateRepository()
        persist(repository, (2, "a", "one"))
        repository._fail_on_history = True
        with self.assertRaises(SyncError):
            persist(repository, (2, "a", "changed"))
        self.assertEqual(1, only_row(repository).version)
        self.assertEqual(1, len(repository.history()))

    def test_state_failure_preserves_previous_version(self) -> None:
        repository = InMemoryRawStateRepository()
        persist(repository, (2, "a", "one"))
        repository._fail_on_commit = True
        with self.assertRaises(SyncError):
            persist(repository, (2, "a", "changed"))
        row = only_row(repository)
        self.assertEqual(1, row.version)
        self.assertFalse(row.is_deleted)

    def test_finish_failure_marks_run_failed_and_reverts_state(self) -> None:
        repository = InMemoryRawStateRepository(fail_on_finish=True)
        with self.assertRaises(SyncError):
            persist(repository, (2, "a", "one"))
        self.assertEqual({}, repository.current_rows(SOURCE_HASH))
        self.assertEqual((), repository.history())
        self.assertEqual("failed", repository.run_status("run-1"))

    def test_concurrent_execution_is_refused_without_waiting(self) -> None:
        repository = InMemoryRawStateRepository()
        self.assertTrue(repository.try_acquire(SOURCE_HASH))
        with self.assertRaises(SyncError) as raised:
            persist(repository, (2, "a", "one"))
        self.assertEqual(ErrorCode.VALIDATION, raised.exception.code)
        repository.release(SOURCE_HASH)
        self.assertIn("pg_try_advisory_xact_lock", PostgresRawRepository.try_lock_sql())


class RawStateSqlAndLogTests(unittest.TestCase):
    def test_state_sql_is_static_parameterized_and_non_destructive(self) -> None:
        hostile = RawRecord(2, "'; drop table x; --", "hash", {"valor": "'); delete from public.raw_current_rows; --"})
        for operation in RawStateOperation:
            statement = PostgresRawRepository.state_command_sql(operation)
            self.assertIn("%s", statement)
            self.assertNotIn("{", statement)
            self.assertNotIn(hostile.key_hash, statement)
            for token in ("drop ", "truncate ", "delete from"):
                self.assertNotIn(token, statement.lower())

    def test_history_statement_carries_classification_and_version(self) -> None:
        statement = PostgresRawRepository.append_raw_row_sql()
        self.assertIn("change_type", statement)
        self.assertIn("row_version", statement)
        self.assertIn("public.raw_import_rows", statement)

    def test_hostile_target_table_is_refused_centrally(self) -> None:
        with self.assertRaises(ValueError):
            RawSyncSource("fixture", SOURCE_HASH, "in-memory-only", "Fixture", "raw; drop table x", ("registro_id",))

    def test_persisted_log_has_counts_without_payload_or_full_hash(self) -> None:
        logger = logging.getLogger("raw-state-test")
        repository = InMemoryRawStateRepository()
        service = RawSynchronizationService(repository, logger)
        with self.assertLogs(logger, "INFO") as captured:
            service.persist_locally(source(), HEADER, rows((2, "a", "valor-confidencial")), NOW)
        line = captured.output[0]
        self.assertIn('"rows_inserted": 1', line)
        self.assertIn('"status": "success"', line)
        for secret in ("valor-confidencial", "registro_id", only_row(repository).key_hash):
            self.assertNotIn(secret, line)

    def test_failure_log_reports_only_sanitized_category(self) -> None:
        logger = logging.getLogger("raw-state-failure-test")
        service = RawSynchronizationService(InMemoryRawStateRepository(fail_on_start=True), logger)
        with self.assertLogs(logger, "INFO") as captured:
            with self.assertRaises(SyncError):
                service.persist_locally(source(), HEADER, rows((2, "a", "valor-confidencial")), NOW)
        line = captured.output[0]
        self.assertIn('"error_code": "database"', line)
        self.assertNotIn("valor-confidencial", line)


class RawStateCommandTests(unittest.TestCase):
    def test_plan_is_translated_into_one_command_per_record(self) -> None:
        previous = build_raw_snapshot(source(), HEADER, rows((2, "a", "one"), (3, "b", "two")), NOW)
        current = build_raw_snapshot(source(), HEADER, rows((2, "a", "changed"), (4, "c", "new")), NOW)
        operations = [command.operation for command in plan_state_commands(compare_raw_snapshots(current, previous))]
        self.assertEqual(
            [RawStateOperation.INSERT, RawStateOperation.UPDATE, RawStateOperation.TOMBSTONE],
            operations,
        )


if __name__ == "__main__":
    unittest.main()
