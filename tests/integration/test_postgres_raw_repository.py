from __future__ import annotations

import os
import unittest
import uuid
from datetime import UTC, datetime

import psycopg

from sheets_supabase_sync.errors import SyncError
from sheets_supabase_sync.raw_repository import PostgresRawRepository, assess_raw_schema
from sheets_supabase_sync.raw_sync import RawInputRow, RawSyncSource
from sheets_supabase_sync.raw_sync_service import RawSynchronizationService


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
    return RawSynchronizationService(repository).persist_locally(source_contract, HEADER, input_rows, NOW)


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


if __name__ == "__main__":
    unittest.main()
