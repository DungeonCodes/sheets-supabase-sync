from __future__ import annotations

import os
import unittest
import uuid

import psycopg


DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")


@unittest.skipUnless(DATABASE_URL, "Defina LOCAL_DATABASE_URL para o Supabase local.")
class RetentionControlsPostgresTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suffix = uuid.uuid4().hex[:10]

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(DATABASE_URL, autocommit=False)

    def insert_source(self, cursor, suffix: str) -> str:
        cursor.execute(
            "insert into public.data_sources "
            "(name, spreadsheet_id, sheet_name, target_table, business_key) "
            "values (%s, %s, 'Fixture', %s, '[\"registro_id\"]'::jsonb) returning id",
            (f"retention-{suffix}", f"sheet-{suffix}", f"retention_{suffix}"),
        )
        return str(cursor.fetchone()[0])

    def assert_rejected(self, cursor, statement: str, parameters=()) -> None:
        cursor.execute("savepoint expected_failure")
        with self.assertRaises(psycopg.Error):
            cursor.execute(statement, parameters)
        cursor.execute("rollback to savepoint expected_failure")
        cursor.execute("release savepoint expected_failure")

    def test_catalog_has_columns_constraints_indexes_rls_and_zero_policies(self) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "select column_name, is_nullable, column_default from information_schema.columns "
                "where table_schema='public' and table_name='data_sources' "
                "and column_name like 'lifecycle_%'"
            )
            columns = {name: (nullable, default) for name, nullable, default in cursor.fetchall()}
            self.assertEqual(
                {"lifecycle_status", "lifecycle_changed_at", "lifecycle_reason_code", "lifecycle_changed_by_ref"},
                set(columns),
            )
            self.assertEqual("NO", columns["lifecycle_status"][0])
            self.assertIn("'active'::text", columns["lifecycle_status"][1])
            self.assertEqual("NO", columns["lifecycle_changed_at"][0])

            cursor.execute(
                "select conname from pg_constraint where connamespace='public'::regnamespace "
                "and conrelid in ('public.data_sources'::regclass, "
                "'public.retention_holds'::regclass, 'public.purge_runs'::regclass)"
            )
            constraints = {row[0] for row in cursor.fetchall()}
            for expected in (
                "data_sources_lifecycle_status_valid",
                "data_sources_lifecycle_enabled_consistent",
                "retention_holds_release_consistent",
                "purge_runs_status_valid",
                "purge_runs_terminal_consistent",
            ):
                self.assertIn(expected, constraints)

            cursor.execute(
                "select indexname from pg_indexes where schemaname='public' "
                "and indexname in ('retention_holds_global_active_idx', "
                "'retention_holds_source_active_idx', 'sync_runs_retention_idx', "
                "'schema_change_requests_retention_idx', 'purge_runs_executable_idx')"
            )
            self.assertEqual(5, len(cursor.fetchall()))

            cursor.execute(
                "select relname, relrowsecurity from pg_class "
                "where oid in ('public.retention_holds'::regclass, 'public.purge_runs'::regclass)"
            )
            self.assertEqual({("retention_holds", True), ("purge_runs", True)}, set(cursor.fetchall()))

            cursor.execute(
                "select conname, confdeltype from pg_constraint where conname in "
                "('raw_current_rows_last_sync_run_id_fkey', "
                "'retention_holds_data_source_id_fkey', 'purge_runs_data_source_id_fkey')"
            )
            self.assertEqual(
                {
                    ("raw_current_rows_last_sync_run_id_fkey", "a"),
                    ("retention_holds_data_source_id_fkey", "n"),
                    ("purge_runs_data_source_id_fkey", "n"),
                },
                set(cursor.fetchall()),
            )

            cursor.execute(
                "select count(*) from pg_policies where schemaname='public' "
                "and tablename in ('retention_holds', 'purge_runs')"
            )
            self.assertEqual(0, cursor.fetchone()[0])
            cursor.execute(
                "select count(*) from pg_trigger "
                "where tgrelid='public.raw_current_rows'::regclass and not tgisinternal"
            )
            self.assertEqual(0, cursor.fetchone()[0])
            cursor.execute(
                "select count(*) from pg_proc where pronamespace='public'::regnamespace "
                "and (proname like 'retention%' or proname like 'purge%')"
            )
            self.assertEqual(0, cursor.fetchone()[0])

    def test_lifecycle_states_and_enabled_consistency(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "select lifecycle_status, enabled from public.data_sources "
                    "where spreadsheet_id='fixture' and sheet_name='Respostas'"
                )
                self.assertEqual(("active", True), cursor.fetchone())
                source_id = self.insert_source(cursor, f"lifecycle_{self.suffix}")
                cursor.execute(
                    "select lifecycle_status, enabled from public.data_sources where id=%s",
                    (source_id,),
                )
                self.assertEqual(("active", True), cursor.fetchone())

                for status in ("suspended", "offboarding", "retired"):
                    cursor.execute(
                        "update public.data_sources set lifecycle_status=%s, enabled=false, "
                        "lifecycle_reason_code='controlled_test', "
                        "lifecycle_changed_by_ref='operator:test' where id=%s",
                        (status, source_id),
                    )
                cursor.execute(
                    "update public.data_sources set lifecycle_status='active', enabled=true, "
                    "lifecycle_reason_code=null, lifecycle_changed_by_ref=null where id=%s",
                    (source_id,),
                )

                self.assert_rejected(
                    cursor,
                    "update public.data_sources set lifecycle_status='invalid' where id=%s",
                    (source_id,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.data_sources set enabled=false where id=%s",
                    (source_id,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.data_sources set lifecycle_status='suspended', "
                    "lifecycle_reason_code='controlled_test', "
                    "lifecycle_changed_by_ref='operator:test' where id=%s",
                    (source_id,),
                )
        finally:
            connection.rollback()
            connection.close()

    def test_global_and_source_holds_are_unique_and_release_is_consistent(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                first = self.insert_source(cursor, f"hold_a_{self.suffix}")
                second = self.insert_source(cursor, f"hold_b_{self.suffix}")
                cursor.execute(
                    "insert into public.retention_holds "
                    "(scope, reason_code, activated_by_ref) "
                    "values ('institution', 'legal_review', 'operator:test')"
                )
                self.assert_rejected(
                    cursor,
                    "insert into public.retention_holds "
                    "(scope, reason_code, activated_by_ref) "
                    "values ('institution', 'second_review', 'operator:test')",
                )

                cursor.execute(
                    "insert into public.retention_holds "
                    "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                    "values ('source', %s, %s, 'legal_review', 'operator:test') returning id",
                    (first, f"source:{self.suffix}:a"),
                )
                first_hold = str(cursor.fetchone()[0])
                self.assert_rejected(
                    cursor,
                    "insert into public.retention_holds "
                    "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                    "values ('source', %s, %s, 'second_review', 'operator:test')",
                    (first, f"source:{self.suffix}:a"),
                )
                cursor.execute(
                    "insert into public.retention_holds "
                    "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                    "values ('source', %s, %s, 'legal_review', 'operator:test') returning id",
                    (second, f"source:{self.suffix}:b"),
                )
                second_hold = str(cursor.fetchone()[0])

                self.assert_rejected(
                    cursor,
                    "update public.retention_holds set released_at=now() where id=%s",
                    (first_hold,),
                )
                cursor.execute(
                    "update public.retention_holds set released_at=now(), "
                    "released_by_ref='operator:release', release_reason_code='review_complete' "
                    "where id=%s",
                    (first_hold,),
                )
                self.assert_rejected(cursor, "delete from public.data_sources where id=%s", (second,))
                cursor.execute(
                    "update public.retention_holds set released_at=now(), "
                    "released_by_ref='operator:release', release_reason_code='review_complete' "
                    "where id=%s",
                    (second_hold,),
                )
                cursor.execute("delete from public.data_sources where id=%s", (second,))
                cursor.execute("select data_source_id from public.retention_holds where id=%s", (second_hold,))
                self.assertIsNone(cursor.fetchone()[0])
        finally:
            connection.rollback()
            connection.close()

    def test_purge_run_contract_and_source_evidence(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                source_id = self.insert_source(cursor, f"purge_{self.suffix}")
                digest = "a" * 64
                cursor.execute(
                    "insert into public.purge_runs "
                    "(data_source_id, source_ref, run_type, policy_ref, policy_version, "
                    "policy_digest, dry_run_digest, cutoffs, candidate_counts) "
                    "values (%s, %s, 'retention', 'policy:local', 'v1', %s, %s, "
                    "'{\"raw_import_rows\":\"2026-01-01T00:00:00Z\"}'::jsonb, "
                    "'{\"raw_import_rows\":0}'::jsonb) returning id",
                    (source_id, f"source:{self.suffix}", digest, digest),
                )
                run_id = str(cursor.fetchone()[0])
                cursor.execute("update public.purge_runs set status='running' where id=%s", (run_id,))
                cursor.execute(
                    "update public.purge_runs set status='completed', finished_at=now(), "
                    "outcome_code='dry_run_complete' where id=%s",
                    (run_id,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set affected_counts='{\"raw_import_rows\":1}'::jsonb "
                    "where id=%s",
                    (run_id,),
                )
                self.assert_rejected(
                    cursor,
                    "insert into public.purge_runs "
                    "(source_ref, run_type, policy_ref, policy_version, policy_digest, "
                    "dry_run_digest, cutoffs) values "
                    "('source:invalid', 'retention', 'policy:local', 'v1', 'short', %s, '{}'::jsonb)",
                    (digest,),
                )
                cursor.execute("delete from public.data_sources where id=%s", (source_id,))
                cursor.execute(
                    "select data_source_id, source_ref, status, dry_run from public.purge_runs where id=%s",
                    (run_id,),
                )
                self.assertEqual((None, f"source:{self.suffix}", "completed", True), cursor.fetchone())
        finally:
            connection.rollback()
            connection.close()

    def test_current_row_keeps_last_sync_run_restrictive(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                source_id = self.insert_source(cursor, f"current_{self.suffix}")
                cursor.execute(
                    "insert into public.sync_runs (data_source_id, status, finished_at) "
                    "values (%s, 'applied', now()) returning id",
                    (source_id,),
                )
                run_id = str(cursor.fetchone()[0])
                cursor.execute(
                    "insert into public.raw_current_rows "
                    "(data_source_id, row_key_hash, content_hash, payload_json, "
                    "source_row_number, last_sync_run_id) "
                    "values (%s, %s, %s, '{}'::jsonb, 1, %s)",
                    (source_id, f"key-{self.suffix}", f"content-{self.suffix}", run_id),
                )
                self.assert_rejected(cursor, "delete from public.sync_runs where id=%s", (run_id,))
                cursor.execute("select count(*) from public.raw_current_rows where last_sync_run_id=%s", (run_id,))
                self.assertEqual(1, cursor.fetchone()[0])
        finally:
            connection.rollback()
            connection.close()

    def test_frontend_denied_and_service_role_is_not_administrative(self) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            for role in ("anon", "authenticated"):
                for table in ("retention_holds", "purge_runs"):
                    for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                        cursor.execute("select has_table_privilege(%s, %s, %s)", (role, f"public.{table}", privilege))
                        self.assertFalse(cursor.fetchone()[0], (role, table, privilege))

            for table in ("retention_holds", "purge_runs"):
                cursor.execute("select has_table_privilege('service_role', %s, 'SELECT')", (f"public.{table}",))
                self.assertTrue(cursor.fetchone()[0])
                for privilege in ("INSERT", "UPDATE", "DELETE"):
                    cursor.execute(
                        "select has_table_privilege('service_role', %s, %s)",
                        (f"public.{table}", privilege),
                    )
                    self.assertFalse(cursor.fetchone()[0], (table, privilege))

            for table in (
                "data_sources",
                "sync_runs",
                "raw_import_rows",
                "raw_current_rows",
                "import_errors",
                "schema_change_requests",
            ):
                cursor.execute("select has_table_privilege('service_role', %s, 'DELETE')", (f"public.{table}",))
                self.assertFalse(cursor.fetchone()[0], table)

            cursor.execute(
                "select has_column_privilege('service_role', 'public.data_sources', "
                "'lifecycle_status', 'UPDATE')"
            )
            self.assertFalse(cursor.fetchone()[0])
            cursor.execute(
                "select has_column_privilege('service_role', 'public.data_sources', "
                "'last_success_at', 'UPDATE')"
            )
            self.assertTrue(cursor.fetchone()[0])


if __name__ == "__main__":
    unittest.main()
