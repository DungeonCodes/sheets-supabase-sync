from __future__ import annotations

import os
import unittest
import uuid
from datetime import UTC, datetime

import psycopg

from sheets_supabase_sync.errors import ErrorCode, SyncError
from sheets_supabase_sync.raw_repository import PostgresRawRepository, assess_raw_schema
from sheets_supabase_sync.raw_sync import RawInputRow, RawSyncSource
from sheets_supabase_sync.raw_sync_service import RawSynchronizationService
from sheets_supabase_sync.retries import RetryPolicy


DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MIGRATIONS = os.path.join(ROOT, "supabase", "migrations")
NOW = datetime(2026, 8, 11, tzinfo=UTC)
HEADER = ("registro_id", "valor")


def assessment():
    parts = []
    for name in sorted(os.listdir(MIGRATIONS)):
        if name.endswith(".sql"):
            with open(os.path.join(MIGRATIONS, name), encoding="utf-8") as handle:
                parts.append(handle.read())
    return assess_raw_schema("\n".join(parts))


def source(suffix: str = "main") -> RawSyncSource:
    return RawSyncSource(
        f"fixture-{suffix}",
        f"source-hash-{suffix}",
        f"sheet-{suffix}",
        "Fixture",
        f"fixture_raw_{suffix}",
        ("registro_id",),
    )


def rows(*items: tuple[int, str, str]) -> tuple[RawInputRow, ...]:
    return tuple(RawInputRow(number, {"registro_id": key, "valor": value}) for number, key, value in items)


def persist(source_contract: RawSyncSource, input_rows: tuple[RawInputRow, ...], failure=None):
    repository = PostgresRawRepository(assessment(), DATABASE_URL, failure)
    execution_id = str(uuid.uuid4())
    service = RawSynchronizationService(
        repository,
        retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.01, max_delay_seconds=0.01, max_elapsed_seconds=1, jitter_ratio=0),
        pause=lambda _: None,
        random_value=lambda: 0,
        execution_id_factory=lambda: execution_id,
    )
    return service.persist_locally(source_contract, HEADER, input_rows, NOW)


@unittest.skipUnless(DATABASE_URL, "Defina LOCAL_DATABASE_URL para o Supabase local.")
class PostgresRawRepositoryIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suffix = uuid.uuid4().hex[:10]

    def scalar(self, sql: str, parameters=()):
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(sql, parameters)
            return cursor.fetchone()[0]

    def source_id(self, contract: RawSyncSource):
        return self.scalar(
            "select id from public.data_sources where spreadsheet_id=%s and sheet_name=%s",
            (contract.spreadsheet_id, contract.sheet_name),
        )

    def test_event_only_lifecycle_and_idempotence(self) -> None:
        contract = source(f"lifecycle_{self.suffix}")
        five = rows(*((index + 2, str(index), f"value-{index}") for index in range(5)))
        first = persist(contract, five)
        identical = persist(contract, five)
        updated_rows = list(five)
        updated_rows[0] = RawInputRow(2, {"registro_id": "0", "valor": "changed"})
        updated = persist(contract, tuple(updated_rows))
        removed = persist(contract, tuple(updated_rows[:-1]))
        restored = persist(contract, tuple(updated_rows))
        reordered = tuple(
            RawInputRow(index + 2, row.values)
            for index, row in enumerate(reversed(updated_rows))
        )
        reorder = persist(contract, reordered)

        data_source_id = self.source_id(contract)
        self.assertEqual(5, self.scalar("select count(*) from public.raw_current_rows where data_source_id=%s", (data_source_id,)))
        self.assertEqual(8, self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s", (data_source_id,)))
        self.assertEqual(6, self.scalar("select count(*) from public.sync_runs where data_source_id=%s and status='applied'", (data_source_id,)))
        self.assertEqual(0, self.scalar("select count(*) from public.import_errors where data_source_id=%s", (data_source_id,)))
        self.assertEqual(5, first.plan.counts["new"])
        self.assertEqual(5, identical.plan.counts["unchanged"])
        self.assertEqual(1, updated.plan.counts["changed"])
        self.assertEqual(1, removed.plan.counts["removed"])
        self.assertEqual(1, restored.plan.counts["restored"])
        self.assertEqual(5, reorder.plan.counts["unchanged"])
        self.assertEqual(0, self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s and change_type not in ('insert','update','tombstone','restore')", (data_source_id,)))
        self.assertEqual(1, self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s and change_type='tombstone' and source_row_number is null and content_hash is null and payload_json is null", (data_source_id,)))
        self.assertEqual(0, self.scalar("select count(*) from public.raw_current_rows where data_source_id=%s and version < 1", (data_source_id,)))

    def test_failures_rollback_every_mutation(self) -> None:
        for point in ("after_sync_run", "after_event", "after_state", "before_commit"):
            contract = source(f"{point}_{self.suffix}")

            def fail(current: str, expected=point) -> None:
                if current == expected:
                    raise RuntimeError("controlled")

            with self.assertRaises(RuntimeError):
                persist(contract, rows((2, "a", "one")), fail)
            self.assertEqual(
                0,
                self.scalar(
                    "select count(*) from public.data_sources where spreadsheet_id=%s and sheet_name=%s",
                    (contract.spreadsheet_id, contract.sheet_name),
                ),
            )

    def test_advisory_locks_are_nonblocking_and_scoped_by_source(self) -> None:
        first = PostgresRawRepository(assessment(), DATABASE_URL)
        second = PostgresRawRepository(assessment(), DATABASE_URL)
        other = PostgresRawRepository(assessment(), DATABASE_URL)
        self.assertTrue(first.try_acquire("same-source"))
        self.assertFalse(second.try_acquire("same-source"))
        self.assertTrue(other.try_acquire("different-source"))
        other.rollback("different-source", None)
        other.release("different-source")
        first.complete()
        first.release("same-source")
        after = PostgresRawRepository(assessment(), DATABASE_URL)
        self.assertTrue(after.try_acquire("same-source"))
        after.rollback("same-source", None)
        after.release("same-source")

    def test_busy_source_creates_no_run_or_raw_rows(self) -> None:
        contract = source(f"busy_{self.suffix}")
        holder = PostgresRawRepository(assessment(), DATABASE_URL)
        self.assertTrue(holder.try_acquire(contract.source_hash))
        try:
            with self.assertRaises(SyncError) as raised:
                persist(contract, rows((2, "a", "one")))
            self.assertEqual(ErrorCode.BUSY, raised.exception.code)
        finally:
            holder.rollback(contract.source_hash, None)
            holder.release(contract.source_hash)
        self.assertEqual(
            0,
            self.scalar(
                "select count(*) from public.data_sources where spreadsheet_id=%s and sheet_name=%s",
                (contract.spreadsheet_id, contract.sheet_name),
            ),
        )

    def test_nonactive_source_is_rejected_before_new_run_or_raw_mutation(self) -> None:
        contract = source(f"lifecycle_guard_{self.suffix}")
        persist(contract, rows((2, "a", "one")))
        data_source_id = self.source_id(contract)
        expected = {
            "sync_runs": self.scalar("select count(*) from public.sync_runs where data_source_id=%s", (data_source_id,)),
            "raw_import_rows": self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s", (data_source_id,)),
            "raw_current_rows": self.scalar("select count(*) from public.raw_current_rows where data_source_id=%s", (data_source_id,)),
        }
        for lifecycle_status in ("suspended", "offboarding", "retired"):
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "update public.data_sources set enabled=false, lifecycle_status=%s, "
                    "lifecycle_reason_code='controlled_test', lifecycle_changed_by_ref='operator:test' where id=%s",
                    (lifecycle_status, data_source_id),
                )
                connection.commit()
            with self.assertRaises(SyncError) as raised:
                persist(contract, rows((2, "a", "changed")))
            self.assertEqual(ErrorCode.SOURCE_INACTIVE, raised.exception.code)
            self.assertFalse(raised.exception.retryable)
            for table, count in expected.items():
                self.assertEqual(count, self.scalar(f"select count(*) from public.{table} where data_source_id=%s", (data_source_id,)))
            with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
                cursor.execute(
                    "update public.data_sources set enabled=true, lifecycle_status='active', "
                    "lifecycle_reason_code=null, lifecycle_changed_by_ref=null where id=%s",
                    (data_source_id,),
                )
                connection.commit()

    def test_retry_after_rollback_reapplies_one_event_and_one_version(self) -> None:
        contract = source(f"retry_{self.suffix}")
        persist(contract, rows((2, "a", "one")))
        failures = 0

        def fail_once(point: str) -> None:
            nonlocal failures
            if point == "after_state":
                failures += 1
                if failures == 1:
                    raise SyncError(ErrorCode.DATABASE_TRANSIENT, "controlled transient", True)

        persist(contract, rows((2, "a", "changed")), fail_once)
        data_source_id = self.source_id(contract)
        self.assertEqual(2, failures)
        self.assertEqual(2, self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s", (data_source_id,)))
        self.assertEqual(2, self.scalar("select version from public.raw_current_rows where data_source_id=%s", (data_source_id,)))
        self.assertEqual(2, self.scalar("select count(*) from public.sync_runs where data_source_id=%s and status='applied'", (data_source_id,)))

    def test_commit_ack_loss_is_ambiguous_and_is_not_retried(self) -> None:
        contract = source(f"ambiguous_{self.suffix}")
        failures = 0

        def lose_ack(point: str) -> None:
            nonlocal failures
            if point == "after_commit":
                failures += 1
                raise OSError("controlled commit acknowledgement loss")

        with self.assertRaises(SyncError) as raised:
            persist(contract, rows((2, "a", "one")), lose_ack)
        self.assertEqual(ErrorCode.AMBIGUOUS_OUTCOME, raised.exception.code)
        self.assertEqual(1, failures)
        data_source_id = self.source_id(contract)
        self.assertEqual(1, self.scalar("select count(*) from public.sync_runs where data_source_id=%s and status='applied'", (data_source_id,)))
        self.assertEqual(1, self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s", (data_source_id,)))
        self.assertEqual(1, self.scalar("select version from public.raw_current_rows where data_source_id=%s", (data_source_id,)))


if __name__ == "__main__":
    unittest.main()
