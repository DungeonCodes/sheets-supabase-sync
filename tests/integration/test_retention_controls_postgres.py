from __future__ import annotations

import os
import unittest
import uuid

import psycopg


DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")
DIGEST = "a" * 64


@unittest.skipUnless(DATABASE_URL, "Defina LOCAL_DATABASE_URL para o Supabase local.")
class RetentionControlsPostgresTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suffix = uuid.uuid4().hex[:10]

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(DATABASE_URL, autocommit=False)

    def insert_source(self, cursor, label: str) -> str:
        normalized = label.replace("-", "_")
        cursor.execute(
            "insert into public.data_sources "
            "(name, spreadsheet_id, sheet_name, target_table, business_key) "
            "values (%s, %s, 'Fixture', %s, '[\"registro_id\"]'::jsonb) returning id",
            (f"retention-{self.suffix}-{label}", f"sheet-{self.suffix}-{label}", f"retention_{self.suffix}_{normalized}"),
        )
        return str(cursor.fetchone()[0])

    def assert_rejected(self, cursor, statement: str, parameters=()) -> None:
        cursor.execute("savepoint expected_failure")
        with self.assertRaises(psycopg.Error):
            cursor.execute(statement, parameters)
        cursor.execute("rollback to savepoint expected_failure")
        cursor.execute("release savepoint expected_failure")

    def release_hold(self, cursor, hold_id: str) -> None:
        cursor.execute(
            "update public.retention_holds set released_at=now(), "
            "released_by_ref='operator:release', release_reason_code='review_complete' where id=%s",
            (hold_id,),
        )

    def insert_purge_run(self, cursor, source_id: str, *, dry_run: bool) -> str:
        cursor.execute(
            "insert into public.purge_runs "
            "(data_source_id, source_ref, run_type, dry_run, policy_ref, policy_version, "
            "policy_digest, dry_run_digest, raw_import_rows_cutoff, candidate_raw_import_rows) "
            "values (%s, %s, 'retention', %s, 'policy:local', 'v1', %s, %s, now(), 0) returning id",
            (source_id, f"source:{self.suffix}", dry_run, DIGEST, DIGEST),
        )
        return str(cursor.fetchone()[0])

    def set_lifecycle(self, cursor, source_id: str, status: str) -> None:
        cursor.execute(
            "update public.data_sources set enabled=false, lifecycle_status=%s, "
            "lifecycle_reason_code='controlled_test', lifecycle_changed_by_ref='operator:test' where id=%s",
            (status, source_id),
        )

    def create_committed_source(self, label: str) -> str:
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            source_id = self.insert_source(cursor, label)
        return source_id

    def delete_committed_source(self, source_id: str) -> None:
        with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
            cursor.execute("delete from public.data_sources where id=%s", (source_id,))

    def test_catalog_has_guards_constraints_indexes_rls_and_zero_policies(self) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "select column_name from information_schema.columns where table_schema='public' "
                "and table_name='purge_runs' order by column_name"
            )
            columns = {row[0] for row in cursor.fetchall()}
            self.assertIn("candidate_raw_import_rows", columns)
            self.assertIn("affected_raw_import_rows", columns)
            self.assertIn("raw_import_rows_cutoff", columns)
            self.assertNotIn("candidate_counts", columns)
            self.assertNotIn("affected_counts", columns)
            self.assertNotIn("cutoffs", columns)

            cursor.execute(
                "select conname from pg_constraint where connamespace='public'::regnamespace "
                "and conrelid='public.purge_runs'::regclass"
            )
            constraints = {row[0] for row in cursor.fetchall()}
            self.assertTrue(
                {
                    "purge_runs_candidate_counts_nonnegative",
                    "purge_runs_affected_counts_nonnegative",
                    "purge_runs_approval_before_start",
                    "purge_runs_finished_status_consistent",
                }.issubset(constraints)
            )

            cursor.execute(
                "select tgname from pg_trigger where tgrelid in "
                "('public.data_sources'::regclass, 'public.sync_runs'::regclass, "
                "'public.raw_import_rows'::regclass, 'public.raw_current_rows'::regclass, "
                "'public.import_errors'::regclass, 'public.schema_change_requests'::regclass, "
                "'public.retention_holds'::regclass, 'public.purge_runs'::regclass) and not tgisinternal"
            )
            triggers = {row[0] for row in cursor.fetchall()}
            self.assertEqual(
                {
                    "sync_runs_lifecycle_guard",
                    "sync_runs_hold_delete_guard",
                    "sync_runs_hold_truncate_guard",
                    "data_sources_hold_lifecycle_guard",
                    "data_sources_hold_delete_guard",
                    "data_sources_hold_truncate_guard",
                    "raw_import_rows_hold_delete_guard",
                    "raw_import_rows_hold_truncate_guard",
                    "raw_current_rows_hold_delete_guard",
                    "raw_current_rows_hold_truncate_guard",
                    "import_errors_hold_delete_guard",
                    "import_errors_hold_truncate_guard",
                    "schema_change_requests_hold_delete_guard",
                    "schema_change_requests_hold_truncate_guard",
                    "retention_holds_released_immutable_guard",
                    "retention_holds_evidence_truncate_guard",
                    "purge_runs_guard",
                    "purge_runs_evidence_truncate_guard",
                },
                triggers,
            )

            cursor.execute(
                "select proname, prosecdef from pg_proc where pronamespace='public'::regnamespace "
                "and proname in ('retention_hold_applies', 'acquire_retention_locks', 'guard_sync_run_lifecycle', "
                "'guard_data_source_hold', 'guard_retention_hold_delete', "
                "'guard_released_retention_hold', 'guard_retention_hold_truncate', "
                "'guard_administrative_evidence_truncate', 'guard_purge_run')"
            )
            functions = cursor.fetchall()
            self.assertEqual(9, len(functions))
            self.assertFalse(any(row[1] for row in functions))

            cursor.execute(
                "select relname, relrowsecurity from pg_class where oid in "
                "('public.retention_holds'::regclass, 'public.purge_runs'::regclass)"
            )
            self.assertEqual({("retention_holds", True), ("purge_runs", True)}, set(cursor.fetchall()))
            cursor.execute(
                "select count(*) from pg_policies where schemaname='public' "
                "and tablename in ('retention_holds', 'purge_runs')"
            )
            self.assertEqual(0, cursor.fetchone()[0])

    def test_database_lifecycle_guard_rejects_direct_service_role_syncs(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                active = self.insert_source(cursor, "active")
                cursor.execute("set local role service_role")
                cursor.execute("insert into public.sync_runs(data_source_id, status) values(%s, 'running')", (active,))
                cursor.execute("reset role")

                for status in ("suspended", "offboarding", "retired"):
                    source_id = self.insert_source(cursor, status)
                    self.set_lifecycle(cursor, source_id, status)
                    cursor.execute("set local role service_role")
                    self.assert_rejected(
                        cursor,
                        "insert into public.sync_runs(data_source_id, status) values(%s, 'running')",
                        (source_id,),
                    )
                    cursor.execute("reset role")
                    cursor.execute("select count(*) from public.raw_import_rows where data_source_id=%s", (source_id,))
                    self.assertEqual(0, cursor.fetchone()[0])
                    cursor.execute("select count(*) from public.raw_current_rows where data_source_id=%s", (source_id,))
                    self.assertEqual(0, cursor.fetchone()[0])
        finally:
            connection.rollback()
            connection.close()

    def test_global_hold_blocks_destructive_lifecycle_and_source_delete_until_release(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "insert into public.retention_holds(scope, reason_code, activated_by_ref) "
                    "values ('institution', 'legal_review', 'operator:test') returning id"
                )
                hold_id = str(cursor.fetchone()[0])
                suspended = self.insert_source(cursor, "suspended")
                self.set_lifecycle(cursor, suspended, "suspended")

                protected = self.insert_source(cursor, "global")
                for status in ("offboarding", "retired"):
                    self.assert_rejected(
                        cursor,
                        "update public.data_sources set enabled=false, lifecycle_status=%s, "
                        "lifecycle_reason_code='controlled_test', lifecycle_changed_by_ref='operator:test' where id=%s",
                        (status, protected),
                    )
                self.assert_rejected(cursor, "delete from public.data_sources where id=%s", (protected,))

                self.release_hold(cursor, hold_id)
                self.set_lifecycle(cursor, protected, "offboarding")
                cursor.execute("delete from public.data_sources where id=%s", (protected,))
        finally:
            connection.rollback()
            connection.close()

    def test_source_hold_blocks_lifecycle_delete_and_record_deletion_until_release(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                source_id = self.insert_source(cursor, "source-hold")
                cursor.execute(
                    "insert into public.retention_holds "
                    "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                    "values ('source', %s, %s, 'legal_review', 'operator:test') returning id",
                    (source_id, f"source:{self.suffix}"),
                )
                hold_id = str(cursor.fetchone()[0])
                for status in ("offboarding", "retired"):
                    self.assert_rejected(
                        cursor,
                        "update public.data_sources set enabled=false, lifecycle_status=%s, "
                        "lifecycle_reason_code='controlled_test', lifecycle_changed_by_ref='operator:test' where id=%s",
                        (status, source_id),
                    )
                self.assert_rejected(cursor, "delete from public.data_sources where id=%s", (source_id,))
                cursor.execute(
                    "insert into public.sync_runs(data_source_id, status, finished_at) values(%s, 'applied', now()) returning id",
                    (source_id,),
                )
                run_id = str(cursor.fetchone()[0])
                cursor.execute(
                    "insert into public.raw_import_rows "
                    "(data_source_id, sync_run_id, source_row_number, row_key_hash, content_hash, payload_json, change_type, row_version) "
                    "values (%s, %s, 1, 'key', 'content', '{}'::jsonb, 'insert', 1)",
                    (source_id, run_id),
                )
                self.assert_rejected(cursor, "delete from public.raw_import_rows where data_source_id=%s", (source_id,))

                self.release_hold(cursor, hold_id)
                cursor.execute("delete from public.raw_import_rows where data_source_id=%s", (source_id,))
                cursor.execute("delete from public.sync_runs where id=%s", (run_id,))
                cursor.execute("delete from public.data_sources where id=%s", (source_id,))
                cursor.execute("select data_source_id from public.retention_holds where id=%s", (hold_id,))
                self.assertIsNone(cursor.fetchone()[0])
                self.assert_rejected(
                    cursor,
                    "update public.retention_holds set reason_code='changed' where id=%s",
                    (hold_id,),
                )
        finally:
            connection.rollback()
            connection.close()

    def test_purge_evidence_enforces_hold_status_and_terminal_invariants(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                source_id = self.insert_source(cursor, "purge-hold")
                cursor.execute(
                    "insert into public.retention_holds(scope, reason_code, activated_by_ref) "
                    "values ('institution', 'legal_review', 'operator:test') returning id"
                )
                global_hold = str(cursor.fetchone()[0])
                destructive = self.insert_purge_run(cursor, source_id, dry_run=False)
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='approved', approved_at='2100-01-01T00:00:00Z', "
                    "approved_by_ref='operator:approve' where id=%s",
                    (destructive,),
                )
                dry_run = self.insert_purge_run(cursor, source_id, dry_run=True)
                cursor.execute(
                    "update public.purge_runs set status='running', started_at='2100-01-02T00:00:00Z', "
                    "executed_by_ref='operator:executor', hold_checked_at='2100-01-01T12:00:00Z' where id=%s",
                    (dry_run,),
                )
                self.release_hold(cursor, global_hold)

                temporal = self.insert_purge_run(cursor, source_id, dry_run=False)
                cursor.execute(
                    "update public.purge_runs set status='approved', approved_at='2100-01-03T00:00:00Z', "
                    "approved_by_ref='operator:approve' where id=%s",
                    (temporal,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='running', started_at='2100-01-02T00:00:00Z', "
                    "executed_by_ref='operator:executor', hold_checked_at='2100-01-02T00:00:00Z' where id=%s",
                    (temporal,),
                )

                no_executor = self.insert_purge_run(cursor, source_id, dry_run=True)
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='running', started_at='2100-01-02T00:00:00Z' where id=%s",
                    (no_executor,),
                )

                no_hold_check = self.insert_purge_run(cursor, source_id, dry_run=False)
                cursor.execute(
                    "update public.purge_runs set status='approved', approved_at='2100-01-01T00:00:00Z', "
                    "approved_by_ref='operator:approve' where id=%s",
                    (no_hold_check,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='running', started_at='2100-01-02T00:00:00Z', "
                    "executed_by_ref='operator:executor' where id=%s",
                    (no_hold_check,),
                )

                completed = self.insert_purge_run(cursor, source_id, dry_run=True)
                cursor.execute(
                    "update public.purge_runs set status='running', started_at='2100-01-01T00:00:00Z', "
                    "executed_by_ref='operator:executor', hold_checked_at='2099-12-31T12:00:00Z' where id=%s",
                    (completed,),
                )
                cursor.execute(
                    "update public.purge_runs set status='completed', finished_at='2100-01-02T00:00:00Z', "
                    "outcome_code='dry_run_complete' where id=%s",
                    (completed,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set policy_digest=%s where id=%s",
                    ("b" * 64, completed),
                )
        finally:
            connection.rollback()
            connection.close()

    def test_purge_state_machine_rejects_partial_execution_and_preserves_valid_paths(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                source_id = self.insert_source(cursor, "state-machine")
                destructive = self.insert_purge_run(cursor, source_id, dry_run=False)
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set started_at=now() where id=%s",
                    (destructive,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set executed_by_ref='operator:executor' where id=%s",
                    (destructive,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set affected_raw_import_rows=1 where id=%s",
                    (destructive,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='completed', finished_at=now(), outcome_code='complete' where id=%s",
                    (destructive,),
                )

                cursor.execute(
                    "update public.purge_runs set status='approved', approved_at='2100-01-01T00:00:00Z', "
                    "approved_by_ref='operator:approve' where id=%s",
                    (destructive,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='completed', finished_at='2100-01-02T00:00:00Z', "
                    "outcome_code='complete' where id=%s",
                    (destructive,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='running', started_at='2099-12-31T00:00:00Z', "
                    "executed_by_ref='operator:executor', hold_checked_at='2099-12-31T00:00:00Z' where id=%s",
                    (destructive,),
                )

                dry_run = self.insert_purge_run(cursor, source_id, dry_run=True)
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='approved', approved_at=now(), "
                    "approved_by_ref='operator:approve' where id=%s",
                    (dry_run,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='running', started_at=now(), "
                    "executed_by_ref='operator:executor' where id=%s",
                    (dry_run,),
                )

                pre_execution = self.insert_purge_run(cursor, source_id, dry_run=False)
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='failed', finished_at=now(), outcome_code='failed', "
                    "affected_raw_import_rows=1 where id=%s",
                    (pre_execution,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='failed', finished_at='2100-01-01T00:00:00Z', "
                    "outcome_code='failed', approved_at='2100-01-02T00:00:00Z', "
                    "approved_by_ref='operator:approve' where id=%s",
                    (pre_execution,),
                )
                cursor.execute(
                    "update public.purge_runs set status='failed', finished_at=now(), outcome_code='pre_execution_failed' "
                    "where id=%s",
                    (pre_execution,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='running' where id=%s",
                    (pre_execution,),
                )

                executed_terminal = self.insert_purge_run(cursor, source_id, dry_run=False)
                cursor.execute(
                    "update public.purge_runs set status='approved', approved_at='2100-01-01T00:00:00Z', "
                    "approved_by_ref='operator:approve' where id=%s",
                    (executed_terminal,),
                )
                cursor.execute(
                    "update public.purge_runs set status='running', started_at='2100-01-02T00:00:00Z', "
                    "executed_by_ref='operator:executor', hold_checked_at='2100-01-01T12:00:00Z' where id=%s",
                    (executed_terminal,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='failed', started_at=null, executed_by_ref=null, "
                    "hold_checked_at=null, finished_at='2100-01-03T00:00:00Z', outcome_code='failed' where id=%s",
                    (executed_terminal,),
                )
                self.assert_rejected(
                    cursor,
                    "update public.purge_runs set status='failed', finished_at='2100-01-03T00:00:00Z', "
                    "outcome_code='failed', affected_raw_import_rows=1 where id=%s",
                    (executed_terminal,),
                )

                cursor.execute(
                    "update public.purge_runs set status='running', started_at='2100-01-02T00:00:00Z', "
                    "executed_by_ref='operator:executor', hold_checked_at='2100-01-01T12:00:00Z' where id=%s",
                    (destructive,),
                )
                cursor.execute(
                    "update public.purge_runs set status='completed', finished_at='2100-01-03T00:00:00Z', "
                    "outcome_code='complete', affected_raw_import_rows=2 where id=%s",
                    (destructive,),
                )
                dry_complete = self.insert_purge_run(cursor, source_id, dry_run=True)
                cursor.execute(
                    "update public.purge_runs set status='running', started_at='2100-01-02T00:00:00Z', "
                    "executed_by_ref='operator:executor', hold_checked_at='2100-01-01T12:00:00Z' where id=%s",
                    (dry_complete,),
                )
                cursor.execute(
                    "update public.purge_runs set status='completed', finished_at='2100-01-03T00:00:00Z', "
                    "outcome_code='dry_run_complete' where id=%s",
                    (dry_complete,),
                )
        finally:
            connection.rollback()
            connection.close()

    def test_release_is_append_only_from_the_first_release_update(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                source_id = self.insert_source(cursor, "release")
                cursor.execute(
                    "insert into public.retention_holds "
                    "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                    "values ('source', %s, %s, 'original_reason', 'operator:original') returning id",
                    (source_id, f"source:{self.suffix}"),
                )
                hold_id = str(cursor.fetchone()[0])
                for assignment in (
                    "reason_code='rewritten_reason'",
                    "activated_by_ref='operator:rewritten'",
                    "activated_at=activated_at + interval '1 second'",
                    "source_ref='source:rewritten'",
                    "scope='institution', data_source_id=null, source_ref=null",
                ):
                    self.assert_rejected(
                        cursor,
                        "update public.retention_holds set released_at=now(), released_by_ref='operator:release', "
                        f"release_reason_code='review_complete', {assignment} where id=%s",
                        (hold_id,),
                    )
                self.release_hold(cursor, hold_id)
                for assignment in (
                    "released_at=null, released_by_ref=null, release_reason_code=null",
                    "released_at=now() + interval '1 second'",
                    "reason_code='rewritten_after_release'",
                    "activated_by_ref='operator:rewritten'",
                ):
                    self.assert_rejected(
                        cursor,
                        f"update public.retention_holds set {assignment} where id=%s",
                        (hold_id,),
                    )
                cursor.execute("delete from public.data_sources where id=%s", (source_id,))
                cursor.execute("select data_source_id from public.retention_holds where id=%s", (hold_id,))
                self.assertIsNone(cursor.fetchone()[0])
        finally:
            connection.rollback()
            connection.close()

    def test_active_hold_blocks_protected_truncate_and_service_role_has_no_truncate(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "insert into public.retention_holds(scope, reason_code, activated_by_ref) "
                    "values ('institution', 'legal_review', 'operator:test')"
                )
                self.assert_rejected(cursor, "truncate public.raw_import_rows")
                cursor.execute(
                    "select has_table_privilege('service_role', 'public.raw_import_rows', 'TRUNCATE')"
                )
                self.assertFalse(cursor.fetchone()[0])
        finally:
            connection.rollback()
            connection.close()

    def test_truncate_without_hold_keeps_local_admin_behavior(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("truncate public.schema_change_requests")
        finally:
            connection.rollback()
            connection.close()

    def test_retention_locks_serialize_global_hold_and_destructive_lifecycle(self) -> None:
        source_id = self.create_committed_source("global-lock")
        first = self.connect()
        second = self.connect()
        try:
            with first.cursor() as cursor:
                self.set_lifecycle(cursor, source_id, "offboarding")
            with second.cursor() as cursor:
                cursor.execute("set lock_timeout='200ms'")
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    cursor.execute(
                        "insert into public.retention_holds(scope, reason_code, activated_by_ref) "
                        "values ('institution', 'legal_review', 'operator:test')"
                    )
            second.rollback()
            first.rollback()
            with first.cursor() as cursor:
                cursor.execute(
                    "insert into public.retention_holds(scope, reason_code, activated_by_ref) "
                    "values ('institution', 'legal_review', 'operator:test')"
                )
            with second.cursor() as cursor:
                cursor.execute("set lock_timeout='200ms'")
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    self.set_lifecycle(cursor, source_id, "offboarding")
            second.rollback()
            first.rollback()
            with second.cursor() as cursor:
                cursor.execute(
                    "insert into public.retention_holds(scope, reason_code, activated_by_ref) "
                    "values ('institution', 'legal_review', 'operator:test')"
                )
            second.rollback()
        finally:
            first.close()
            second.close()
            self.delete_committed_source(source_id)

    def test_retention_locks_serialize_source_hold_and_destructive_lifecycle(self) -> None:
        source_id = self.create_committed_source("source-lock")
        first = self.connect()
        second = self.connect()
        try:
            with first.cursor() as cursor:
                self.set_lifecycle(cursor, source_id, "offboarding")
            with second.cursor() as cursor:
                cursor.execute("set lock_timeout='200ms'")
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    cursor.execute(
                        "insert into public.retention_holds "
                        "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                        "values ('source', %s, %s, 'legal_review', 'operator:test')",
                        (source_id, f"source:{self.suffix}"),
                    )
            second.rollback()
            first.rollback()
            with first.cursor() as cursor:
                cursor.execute(
                    "insert into public.retention_holds "
                    "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                    "values ('source', %s, %s, 'legal_review', 'operator:test')",
                    (source_id, f"source:{self.suffix}"),
                )
            with second.cursor() as cursor:
                cursor.execute("set lock_timeout='200ms'")
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    self.set_lifecycle(cursor, source_id, "offboarding")
            second.rollback()
            first.rollback()
            with second.cursor() as cursor:
                cursor.execute(
                    "insert into public.retention_holds "
                    "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                    "values ('source', %s, %s, 'legal_review', 'operator:test')",
                    (source_id, f"source:{self.suffix}"),
                )
            second.rollback()
        finally:
            first.close()
            second.close()
            self.delete_committed_source(source_id)

    def test_retention_lock_is_released_after_commit(self) -> None:
        source_id = self.create_committed_source("commit-lock")
        first = self.connect()
        second = self.connect()
        try:
            with first.cursor() as cursor:
                cursor.execute(
                    "insert into public.retention_holds "
                    "(scope, data_source_id, source_ref, reason_code, activated_by_ref) "
                    "values ('source', %s, %s, 'legal_review', 'operator:test') returning id",
                    (source_id, f"source:{self.suffix}"),
                )
                hold_id = str(cursor.fetchone()[0])
            first.commit()
            with second.cursor() as cursor:
                cursor.execute("set lock_timeout='200ms'")
                cursor.execute(
                    "update public.retention_holds set released_at=now(), released_by_ref='operator:release', "
                    "release_reason_code='review_complete' where id=%s",
                    (hold_id,),
                )
            second.commit()
        finally:
            first.close()
            second.close()
            self.delete_committed_source(source_id)

    def test_purge_counts_are_typed_nonnegative_and_have_no_json_surface(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                source_id = self.insert_source(cursor, "counts")
                self.assert_rejected(
                    cursor,
                    "insert into public.purge_runs "
                    "(data_source_id, source_ref, run_type, policy_ref, policy_version, policy_digest, dry_run_digest, "
                    "candidate_raw_import_rows) values (%s, %s, 'retention', 'policy:local', 'v1', %s, %s, -1)",
                    (source_id, f"source:{self.suffix}", DIGEST, DIGEST),
                )
                self.assert_rejected(
                    cursor,
                    "insert into public.purge_runs "
                    "(data_source_id, source_ref, run_type, policy_ref, policy_version, policy_digest, dry_run_digest, "
                    "candidate_raw_import_rows) values (%s, %s, 'retention', 'policy:local', 'v1', %s, %s, 'payload')",
                    (source_id, f"source:{self.suffix}", DIGEST, DIGEST),
                )
                self.assert_rejected(
                    cursor,
                    "insert into public.purge_runs "
                    "(data_source_id, source_ref, run_type, policy_ref, policy_version, policy_digest, dry_run_digest, candidate_counts) "
                    "values (%s, %s, 'retention', 'policy:local', 'v1', %s, %s, '{\"unknown\":1}'::jsonb)",
                    (source_id, f"source:{self.suffix}", DIGEST, DIGEST),
                )
        finally:
            connection.rollback()
            connection.close()

    def test_technical_refs_reject_email_url_spaces_and_free_text(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                source_id = self.insert_source(cursor, "refs")
                for invalid_ref in ("person@example.com", "https://example.invalid", "human name", "actor/invalid"):
                    self.assert_rejected(
                        cursor,
                        "insert into public.retention_holds(scope, reason_code, activated_by_ref) "
                        "values ('institution', 'legal_review', %s)",
                        (invalid_ref,),
                    )
                    self.assert_rejected(
                        cursor,
                        "insert into public.purge_runs "
                        "(data_source_id, source_ref, run_type, policy_ref, policy_version, policy_digest, dry_run_digest) "
                        "values (%s, %s, 'retention', 'policy:local', 'v1', %s, %s)",
                        (source_id, invalid_ref, DIGEST, DIGEST),
                    )
                self.assert_rejected(
                    cursor,
                    "update public.data_sources set enabled=false, lifecycle_status='suspended', "
                    "lifecycle_reason_code='controlled_test', lifecycle_changed_by_ref='person@example.com' where id=%s",
                    (source_id,),
                )
        finally:
            connection.rollback()
            connection.close()

    def test_current_run_fk_and_least_privilege_remain_restrictive(self) -> None:
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                source_id = self.insert_source(cursor, "current")
                cursor.execute(
                    "insert into public.sync_runs (data_source_id, status, finished_at) values (%s, 'applied', now()) returning id",
                    (source_id,),
                )
                run_id = str(cursor.fetchone()[0])
                cursor.execute(
                    "insert into public.raw_current_rows "
                    "(data_source_id, row_key_hash, content_hash, payload_json, source_row_number, last_sync_run_id) "
                    "values (%s, %s, %s, '{}'::jsonb, 1, %s)",
                    (source_id, f"key-{self.suffix}", f"content-{self.suffix}", run_id),
                )
                self.assert_rejected(cursor, "delete from public.sync_runs where id=%s", (run_id,))
                for role in ("anon", "authenticated"):
                    for table in ("retention_holds", "purge_runs"):
                        cursor.execute("select has_table_privilege(%s, %s, 'SELECT')", (role, f"public.{table}"))
                        self.assertFalse(cursor.fetchone()[0])
                for table in ("retention_holds", "purge_runs"):
                    cursor.execute("select has_table_privilege('service_role', %s, 'SELECT')", (f"public.{table}",))
                    self.assertTrue(cursor.fetchone()[0])
                    cursor.execute("select has_table_privilege('service_role', %s, 'DELETE')", (f"public.{table}",))
                    self.assertFalse(cursor.fetchone()[0])
                cursor.execute(
                    "select has_column_privilege('service_role', 'public.data_sources', 'lifecycle_status', 'UPDATE')"
                )
                self.assertFalse(cursor.fetchone()[0])
        finally:
            connection.rollback()
            connection.close()


if __name__ == "__main__":
    unittest.main()
