from __future__ import annotations

import csv
import os
import unittest
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from sheets_supabase_sync.errors import ErrorCode, SyncError
from sheets_supabase_sync.operational_events import OperationalEvent
from sheets_supabase_sync.raw_repository import PostgresRawRepository, assess_raw_schema
from sheets_supabase_sync.raw_sync import RawInputRow, RawSyncSource
from sheets_supabase_sync.raw_sync_service import RawSynchronizationService
from sheets_supabase_sync.retries import RetryPolicy


DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")
ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 9, 2, tzinfo=UTC)


def assessment():
    sql = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / "supabase" / "migrations").glob("*.sql")))
    return assess_raw_schema(sql)


def fixture(name: str) -> tuple[tuple[str, ...], tuple[RawInputRow, ...]]:
    with (ROOT / "data" / "fixtures" / name).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ()), tuple(RawInputRow(index, row) for index, row in enumerate(reader, 2))


@unittest.skipUnless(DATABASE_URL, "Defina LOCAL_DATABASE_URL para o Supabase local.")
class MultiSourcePostgresTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suffix = uuid.uuid4().hex[:10]
        self.source_a = RawSyncSource(
            f"fixture-a-{self.suffix}",
            f"source-a-safe-{self.suffix}",
            f"fixture-sheet-a-{self.suffix}",
            "Cursos",
            f"multi_source_a_{self.suffix}",
            ("registro_id",),
        )
        self.source_b = RawSyncSource(
            f"fixture-b-{self.suffix}",
            f"source-b-safe-{self.suffix}",
            f"fixture-sheet-b-{self.suffix}",
            "Pontuacoes",
            f"multi_source_b_{self.suffix}",
            ("registro_id",),
        )
        self.header_a, self.rows_a = fixture("multi_source_a.csv")
        self.header_b, self.rows_b = fixture("multi_source_b.csv")

    def tearDown(self) -> None:
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "select id from public.data_sources where spreadsheet_id in (%s, %s)",
                (self.source_a.spreadsheet_id, self.source_b.spreadsheet_id),
            )
            for (source_id,) in cursor.fetchall():
                cursor.execute("delete from public.retention_holds where data_source_id=%s", (source_id,))
                cursor.execute("delete from public.schema_change_requests where data_source_id=%s", (source_id,))
                cursor.execute("delete from public.import_errors where data_source_id=%s", (source_id,))
                cursor.execute("delete from public.raw_import_rows where data_source_id=%s", (source_id,))
                cursor.execute("delete from public.raw_current_rows where data_source_id=%s", (source_id,))
                cursor.execute("delete from public.sync_runs where data_source_id=%s", (source_id,))
                cursor.execute("delete from public.data_sources where id=%s", (source_id,))

    def scalar(self, sql: str, parameters=()):
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(sql, parameters)
            return cursor.fetchone()[0]

    def source_id(self, source: RawSyncSource) -> str:
        return str(
            self.scalar(
                "select id from public.data_sources where spreadsheet_id=%s and sheet_name=%s",
                (source.spreadsheet_id, source.sheet_name),
            )
        )

    def fingerprint(self, source_id: str) -> tuple[tuple[object, ...], ...]:
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "select row_key_hash, content_hash, payload_json::text, source_row_number, is_deleted, version "
                "from public.raw_current_rows where data_source_id=%s order by row_key_hash",
                (source_id,),
            )
            return tuple(cursor.fetchall())

    def persist(
        self,
        source: RawSyncSource,
        header: tuple[str, ...],
        rows: tuple[RawInputRow, ...],
        *,
        failure=None,
        reporter=None,
    ):
        service = RawSynchronizationService(
            PostgresRawRepository(assessment(), DATABASE_URL, failure),
            retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.01, max_delay_seconds=0.01, max_elapsed_seconds=1, jitter_ratio=0),
            pause=lambda _: None,
            random_value=lambda: 0,
            execution_id_factory=lambda: str(uuid.uuid4()),
            reporter=reporter,
        )
        return service.persist_locally(source, header, rows, NOW)

    def test_two_sources_remain_independent_across_the_operational_cycle(self) -> None:
        first_a = self.persist(self.source_a, self.header_a, self.rows_a)
        first_b = self.persist(self.source_b, self.header_b, self.rows_b)
        source_a_id = self.source_id(self.source_a)
        source_b_id = self.source_id(self.source_b)

        self.assertNotEqual(source_a_id, source_b_id)
        self.assertNotEqual(self.header_a, self.header_b)
        self.assertEqual(2, first_a.plan.counts["new"])
        self.assertEqual(2, first_b.plan.counts["new"])
        self.assertEqual({1}, {row[-1] for row in self.fingerprint(source_a_id)})
        self.assertEqual({1}, {row[-1] for row in self.fingerprint(source_b_id)})
        self.assertEqual(1, self.scalar("select count(*) from public.sync_runs where data_source_id=%s", (source_a_id,)))
        self.assertEqual(1, self.scalar("select count(*) from public.sync_runs where data_source_id=%s", (source_b_id,)))
        self.assertEqual(0, self.scalar("select count(*) from public.schema_change_requests where data_source_id in (%s, %s)", (source_a_id, source_b_id)))
        key_hash_a = self.scalar(
            "select row_key_hash from public.raw_current_rows where data_source_id=%s and payload_json->>'registro_id'='1001'",
            (source_a_id,),
        )
        key_hash_b = self.scalar(
            "select row_key_hash from public.raw_current_rows where data_source_id=%s and payload_json->>'registro_id'='1001'",
            (source_b_id,),
        )
        self.assertEqual(key_hash_a, key_hash_b)
        self.assertEqual(2, self.scalar("select count(*) from public.raw_current_rows where data_source_id=%s", (source_a_id,)))
        self.assertEqual(2, self.scalar("select count(*) from public.raw_current_rows where data_source_id=%s", (source_b_id,)))

        history_a = self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s", (source_a_id,))
        history_b = self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s", (source_b_id,))
        identical_a = self.persist(self.source_a, self.header_a, self.rows_a)
        unchanged_b = self.fingerprint(source_b_id)
        identical_b = self.persist(self.source_b, self.header_b, self.rows_b)
        self.assertEqual(2, identical_a.plan.counts["unchanged"])
        self.assertEqual(2, identical_b.plan.counts["unchanged"])
        self.assertEqual(history_a, self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s", (source_a_id,)))
        self.assertEqual(history_b, self.scalar("select count(*) from public.raw_import_rows where data_source_id=%s", (source_b_id,)))
        self.assertEqual(unchanged_b, self.fingerprint(source_b_id))

        updated_a = list(self.rows_a)
        updated_a[0] = RawInputRow(2, {"registro_id": "1001", "curso": "curso_alpha", "status": "concluido"})
        self.persist(self.source_a, self.header_a, tuple(updated_a))
        self.assertEqual(unchanged_b, self.fingerprint(source_b_id))
        unchanged_a = self.fingerprint(source_a_id)
        updated_b = list(self.rows_b)
        updated_b[0] = RawInputRow(2, {"registro_id": "1001", "categoria": "categoria_x", "pontuacao": "11"})
        self.persist(self.source_b, self.header_b, tuple(updated_b))
        self.assertEqual(unchanged_a, self.fingerprint(source_a_id))

        before_tombstone_b = self.fingerprint(source_b_id)
        removed_a = self.persist(self.source_a, self.header_a, tuple(updated_a[:1]))
        restored_a = self.persist(self.source_a, self.header_a, tuple(updated_a))
        self.assertEqual(1, removed_a.plan.counts["removed"])
        self.assertEqual(1, restored_a.plan.counts["restored"])
        self.assertEqual(before_tombstone_b, self.fingerprint(source_b_id))

        drift_rows = tuple(RawInputRow(row.source_row_number, {**row.values, "extra": "fixture"}) for row in updated_a)
        with self.assertRaises(SyncError) as drift:
            self.persist(self.source_a, self.header_a + ("extra",), drift_rows)
        self.assertEqual(ErrorCode.SCHEMA, drift.exception.code)
        self.assertEqual(1, self.scalar("select count(*) from public.schema_change_requests where data_source_id=%s", (source_a_id,)))
        self.assertEqual(0, self.scalar("select count(*) from public.schema_change_requests where data_source_id=%s", (source_b_id,)))
        self.assertEqual(2, self.persist(self.source_b, self.header_b, tuple(updated_b)).plan.counts["unchanged"])

        holder_a = PostgresRawRepository(assessment(), DATABASE_URL)
        self.assertTrue(holder_a.try_acquire(self.source_a.source_hash))
        with self.assertRaises(SyncError) as busy_a:
            self.persist(self.source_a, self.header_a, tuple(updated_a))
        self.assertEqual(ErrorCode.BUSY, busy_a.exception.code)
        self.assertEqual(2, self.persist(self.source_b, self.header_b, tuple(updated_b)).plan.counts["unchanged"])
        holder_a.rollback(self.source_a.source_hash, None)
        holder_a.release(self.source_a.source_hash)

        before_failure_a = self.fingerprint(source_a_id)
        before_failure_b = self.fingerprint(source_b_id)
        events: list[OperationalEvent] = []

        def fail_a(point: str) -> None:
            if point == "after_state":
                raise RuntimeError("controlled")

        failed_rows_a = list(updated_a)
        failed_rows_a[0] = RawInputRow(2, {"registro_id": "1001", "curso": "curso_alpha", "status": "falha_controlada"})
        with self.assertRaises(RuntimeError):
            self.persist(self.source_a, self.header_a, tuple(failed_rows_a), failure=fail_a, reporter=events.append)
        self.assertEqual(before_failure_a, self.fingerprint(source_a_id))
        self.assertEqual(before_failure_b, self.fingerprint(source_b_id))
        self.assertEqual(2, self.persist(self.source_b, self.header_b, tuple(updated_b)).plan.counts["unchanged"])
        self.assertTrue(events)
        self.assertTrue(all(event.source_ref == self.source_a.source_hash[:12] for event in events))
        serialized_events = " ".join(event.as_json() for event in events)
        self.assertNotIn(self.source_a.spreadsheet_id, serialized_events)
        self.assertNotIn("falha_controlada", serialized_events)

        retry_attempts = 0

        def retry_a(point: str) -> None:
            nonlocal retry_attempts
            if point == "after_state":
                retry_attempts += 1
                if retry_attempts == 1:
                    raise SyncError(ErrorCode.DATABASE_TRANSIENT, "controlled", True)

        retry_rows_a = list(updated_a)
        retry_rows_a[0] = RawInputRow(2, {"registro_id": "1001", "curso": "curso_alpha", "status": "revisado"})
        before_retry_b = self.fingerprint(source_b_id)
        self.persist(self.source_a, self.header_a, tuple(retry_rows_a), failure=retry_a)
        self.assertEqual(2, retry_attempts)
        self.assertEqual(before_retry_b, self.fingerprint(source_b_id))

        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "update public.data_sources set enabled=false, lifecycle_status='suspended', "
                "lifecycle_reason_code='controlled_test', lifecycle_changed_by_ref='operator:test' where id=%s",
                (source_a_id,),
            )
        with self.assertRaises(SyncError) as inactive:
            self.persist(self.source_a, self.header_a, tuple(retry_rows_a))
        self.assertEqual(ErrorCode.SOURCE_INACTIVE, inactive.exception.code)
        self.assertFalse(inactive.exception.retryable)
        self.assertEqual(2, self.persist(self.source_b, self.header_b, tuple(updated_b)).plan.counts["unchanged"])
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute(
                "update public.data_sources set enabled=true, lifecycle_status='active', "
                "lifecycle_reason_code=null, lifecycle_changed_by_ref=null where id=%s",
                (source_a_id,),
            )
            cursor.execute(
                "insert into public.retention_holds "
                "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                "values ('source', %s, %s, 'controlled_test', 'operator:test') returning id",
                (source_a_id, f"source:{self.suffix}"),
            )
            hold_id = cursor.fetchone()[0]
            cursor.execute("select public.retention_hold_applies(%s), public.retention_hold_applies(%s)", (source_a_id, source_b_id))
            applies_a, applies_b = cursor.fetchone()
            self.assertTrue(applies_a)
            self.assertFalse(applies_b)
            cursor.execute(
                "update public.retention_holds set released_at=now(), released_by_ref='operator:test', "
                "release_reason_code='controlled_test_complete' where id=%s",
                (hold_id,),
            )


if __name__ == "__main__":
    unittest.main()
