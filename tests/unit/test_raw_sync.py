from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path

from sheets_supabase_sync.errors import ErrorCode, SyncError
from sheets_supabase_sync.raw_repository import InMemoryRawStateRepository, PostgresRawRepository, assess_raw_schema
from sheets_supabase_sync.raw_sync import RawInputRow, RawSyncSource, apply_tombstones, build_raw_snapshot, compare_raw_snapshots
from sheets_supabase_sync.raw_sync_service import RawSynchronizationService


NOW = datetime(2026, 8, 6, tzinfo=UTC)
MIGRATIONS = Path(__file__).parents[2] / "supabase" / "migrations"
BASELINE = MIGRATIONS / "20260804000000_initial_isolated_institution_schema.sql"


def source() -> RawSyncSource:
    return RawSyncSource("fixture", "source-hash", "in-memory-only", "Fixture", "fixture_raw_future", ("registro_id",))


def rows(*items: tuple[int, str, str]) -> tuple[RawInputRow, ...]:
    return tuple(RawInputRow(number, {"registro_id": key, "valor": value}) for number, key, value in items)


def snapshot(*items: tuple[int, str, str]):
    return build_raw_snapshot(source(), ("registro_id", "valor"), rows(*items), NOW)


class RawSyncTests(unittest.TestCase):
    def test_first_load_is_all_new(self) -> None:
        plan = compare_raw_snapshots(snapshot((2, "a", "one"), (3, "b", "two")), None)
        self.assertEqual({"new": 2, "changed": 0, "removed": 0, "restored": 0, "unchanged": 0}, plan.counts)

    def test_identical_second_load_is_unchanged(self) -> None:
        previous = snapshot((2, "a", "one"))
        plan = compare_raw_snapshots(snapshot((2, "a", "one")), previous)
        self.assertEqual({"new": 0, "changed": 0, "removed": 0, "restored": 0, "unchanged": 1}, plan.counts)

    def test_added_record_is_new(self) -> None:
        plan = compare_raw_snapshots(snapshot((2, "a", "one"), (3, "b", "two")), snapshot((2, "a", "one")))
        self.assertEqual(1, len(plan.new))

    def test_content_change_is_detected(self) -> None:
        plan = compare_raw_snapshots(snapshot((2, "a", "changed")), snapshot((2, "a", "one")))
        self.assertEqual(1, len(plan.changed))

    def test_missing_record_is_logical_removal(self) -> None:
        plan = compare_raw_snapshots(snapshot((2, "a", "one")), snapshot((2, "a", "one"), (3, "b", "two")))
        self.assertEqual(1, len(plan.removed))
        self.assertTrue(apply_tombstones(plan).records[plan.removed[0].key_hash].deleted)

    def test_tombstone_is_restored_without_new_identity(self) -> None:
        previous_plan = compare_raw_snapshots(snapshot((2, "a", "one")), snapshot((2, "a", "one"), (3, "b", "two")))
        tombstoned = apply_tombstones(previous_plan)
        plan = compare_raw_snapshots(snapshot((8, "a", "one"), (9, "b", "two")), tombstoned)
        self.assertEqual(1, len(plan.restored))
        self.assertEqual(0, len(plan.new))

    def test_reordered_rows_do_not_change_snapshot_or_content(self) -> None:
        first = snapshot((2, "a", "one"), (3, "b", "two"))
        reordered = snapshot((2, "b", "two"), (3, "a", "one"))
        self.assertEqual(first.snapshot_hash, reordered.snapshot_hash)
        self.assertEqual(2, len(compare_raw_snapshots(reordered, first).unchanged))

    def test_duplicate_key_is_rejected(self) -> None:
        with self.assertRaises(SyncError) as raised:
            snapshot((2, "a", "one"), (3, "a", "two"))
        self.assertEqual(ErrorCode.VALIDATION, raised.exception.code)

    def test_empty_key_is_rejected(self) -> None:
        with self.assertRaises(SyncError) as raised:
            snapshot((2, "", "one"))
        self.assertEqual(ErrorCode.VALIDATION, raised.exception.code)

    def test_hash_is_deterministic(self) -> None:
        self.assertEqual(snapshot((2, "a", "one")).snapshot_hash, snapshot((9, "a", "one")).snapshot_hash)

    def test_dry_run_never_persists(self) -> None:
        result = RawSynchronizationService().dry_run(source(), ("registro_id", "valor"), rows((2, "a", "one")), NOW)
        self.assertFalse(result.persisted)
        self.assertEqual(0, result.metrics.rows_persisted)

    def test_local_commit_is_idempotent(self) -> None:
        repository = InMemoryRawStateRepository()
        service = RawSynchronizationService(repository)
        first = service.persist_locally(source(), ("registro_id", "valor"), rows((2, "a", "one")), NOW)
        second = service.persist_locally(source(), ("registro_id", "valor"), rows((2, "a", "one")), NOW)
        self.assertEqual(1, first.metrics.rows_persisted)
        self.assertEqual(0, second.metrics.rows_persisted)

    def test_commit_failure_preserves_last_valid_snapshot(self) -> None:
        repository = InMemoryRawStateRepository()
        service = RawSynchronizationService(repository)
        service.persist_locally(source(), ("registro_id", "valor"), rows((2, "a", "one")), NOW)
        repository._fail_on_commit = True
        with self.assertRaises(SyncError):
            service.persist_locally(source(), ("registro_id", "valor"), rows((2, "a", "changed")), NOW)
        saved = repository.load_snapshot("source-hash")
        self.assertEqual(snapshot((2, "a", "one")).snapshot_hash, saved.snapshot_hash)

    def test_start_and_finish_failures_rollback_without_snapshot(self) -> None:
        for repository in (InMemoryRawStateRepository(fail_on_start=True), InMemoryRawStateRepository(fail_on_finish=True)):
            with self.assertRaises(SyncError):
                RawSynchronizationService(repository).persist_locally(source(), ("registro_id", "valor"), rows((2, "a", "one")), NOW)
            self.assertIsNone(repository.load_snapshot("source-hash"))

    def test_concurrent_run_is_rejected_without_wait(self) -> None:
        repository = InMemoryRawStateRepository()
        self.assertTrue(repository.try_acquire("source-hash"))
        with self.assertRaises(SyncError):
            RawSynchronizationService(repository).persist_locally(source(), ("registro_id", "valor"), rows((2, "a", "one")), NOW)
        repository.release("source-hash")

    def test_baseline_alone_does_not_support_current_state(self) -> None:
        assessment = assess_raw_schema(BASELINE.read_text(encoding="utf-8"))
        self.assertFalse(assessment.supports_phase_2a)
        self.assertIn("raw_current_rows.table", assessment.missing_capabilities)
        with self.assertRaises(SyncError) as raised:
            PostgresRawRepository(assessment).assert_supported()
        self.assertEqual(ErrorCode.SCHEMA, raised.exception.code)

    def test_incremental_migration_unlocks_current_state(self) -> None:
        declared = "\n".join(path.read_text(encoding="utf-8") for path in sorted(MIGRATIONS.glob("*.sql")))
        assessment = assess_raw_schema(declared)
        self.assertTrue(assessment.supports_phase_2a)
        self.assertEqual((), assessment.missing_capabilities)
        PostgresRawRepository(assessment).assert_supported()

    def test_postgres_sql_is_parameterized_and_has_transaction_lock(self) -> None:
        statements = (
            PostgresRawRepository.find_source_sql(),
            PostgresRawRepository.register_source_sql(),
            PostgresRawRepository.start_run_sql(),
            PostgresRawRepository.append_raw_row_sql(),
            PostgresRawRepository.record_error_sql(),
            PostgresRawRepository.update_source_success_sql(),
            PostgresRawRepository.update_source_failure_sql(),
        )
        for statement in statements:
            self.assertIn("%s", statement)
        self.assertIn("pg_try_advisory_xact_lock", PostgresRawRepository.try_lock_sql())
        self.assertNotIn("registro_id", PostgresRawRepository.append_raw_row_sql())

    def test_raw_modules_do_not_depend_on_google_transport(self) -> None:
        repository_source = (Path(__file__).parents[2] / "src" / "sheets_supabase_sync" / "raw_repository.py").read_text(encoding="utf-8")
        self.assertNotIn("google_", repository_source)


if __name__ == "__main__":
    unittest.main()
