from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path

from sheets_supabase_sync.artifacts import scan_secrets


ROOT = Path(__file__).parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
PATH = MIGRATIONS / "20260825120000_add_retention_controls.sql"
APPLIED_DIGESTS = {
    "20260804000000_initial_isolated_institution_schema.sql": "53f6326e1c50e9ddd6c50037e40d00ad7afc26c290fc53e64ebd1358fdae2f5d",
    "20260806120000_add_raw_current_state.sql": "c3bd0000f19627fd21fe970f1aa06df801e99c195a5202f790ca09cfc0bcf06d",
    "20260811150000_make_raw_import_event_only.sql": "43a0eba90a8665699ff2499966ca5492899a03d62929487fae8ee9bb6bb17ef1",
}


class RetentionControlsMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = PATH.read_text(encoding="utf-8").lower()

    def test_is_exactly_the_fourth_migration(self) -> None:
        migrations = sorted(MIGRATIONS.glob("*.sql"))
        self.assertEqual(4, len(migrations))
        self.assertEqual(PATH, migrations[3])

    def test_applied_migrations_remain_byte_identical(self) -> None:
        for name, expected in APPLIED_DIGESTS.items():
            digest = hashlib.sha256((MIGRATIONS / name).read_bytes()).hexdigest()
            self.assertEqual(expected, digest, name)

    def test_lifecycle_is_closed_and_consistent_with_enabled(self) -> None:
        for column in (
            "lifecycle_status text not null default 'active'",
            "lifecycle_changed_at timestamptz not null default now()",
            "lifecycle_reason_code text",
            "lifecycle_changed_by_ref text",
        ):
            self.assertIn(column, self.sql)
        self.assertIn("lifecycle_status in ('active', 'suspended', 'offboarding', 'retired')", self.sql)
        self.assertIn("lifecycle_status = 'active' and enabled", self.sql)
        self.assertIn("lifecycle_status <> 'active' and not enabled", self.sql)
        self.assertIn("where not enabled", self.sql)
        self.assertIn("create function public.guard_sync_run_lifecycle()", self.sql)
        self.assertIn("create trigger sync_runs_lifecycle_guard", self.sql)
        self.assertIn("data source is not synchronizable", self.sql)

    def test_hold_table_has_scope_release_and_active_uniqueness(self) -> None:
        self.assertIn("create table public.retention_holds", self.sql)
        self.assertIn("scope in ('institution', 'source')", self.sql)
        self.assertIn("data_source_id uuid references public.data_sources(id) on delete set null", self.sql)
        self.assertIn("retention_holds_release_consistent", self.sql)
        self.assertIn("create unique index retention_holds_global_active_idx", self.sql)
        self.assertIn("create unique index retention_holds_source_active_idx", self.sql)
        self.assertIn("create function public.retention_hold_applies(target_data_source_id uuid)", self.sql)
        self.assertIn("create function public.acquire_retention_locks(target_data_source_id uuid)", self.sql)
        self.assertIn("pg_advisory_xact_lock", self.sql)
        self.assertIn("retention:institution", self.sql)
        self.assertIn("retention:source:", self.sql)
        self.assertIn("create trigger data_sources_hold_lifecycle_guard", self.sql)
        self.assertIn("create trigger data_sources_hold_delete_guard", self.sql)
        self.assertIn("create trigger raw_import_rows_hold_delete_guard", self.sql)
        self.assertIn("create trigger retention_holds_released_immutable_guard", self.sql)
        self.assertIn("retention hold release cannot rewrite activation evidence", self.sql)
        self.assertIn("before insert or update on public.retention_holds", self.sql)
        self.assertIn("create function public.guard_retention_hold_truncate()", self.sql)
        self.assertIn("create function public.guard_administrative_evidence_truncate()", self.sql)

    def test_purge_runs_store_only_aggregate_evidence(self) -> None:
        self.assertIn("create table public.purge_runs", self.sql)
        self.assertIn("status in ('planned', 'approved', 'running', 'completed', 'failed', 'cancelled')", self.sql)
        self.assertIn("dry_run boolean not null default true", self.sql)
        self.assertIn("policy_digest text not null", self.sql)
        self.assertIn("candidate_raw_import_rows bigint not null default 0", self.sql)
        self.assertIn("affected_raw_import_rows bigint not null default 0", self.sql)
        self.assertIn("purge_runs_candidate_counts_nonnegative", self.sql)
        self.assertIn("purge_runs_affected_counts_nonnegative", self.sql)
        self.assertIn("raw_import_rows_cutoff timestamptz", self.sql)
        self.assertIn("create function public.guard_purge_run()", self.sql)
        self.assertIn("terminal purge evidence is immutable", self.sql)
        self.assertIn("purge_runs_approval_before_finish", self.sql)
        self.assertIn("planned purge run cannot contain execution evidence", self.sql)
        self.assertIn("pre-execution terminal cannot contain execution evidence", self.sql)
        self.assertIn("running purge run requires start, executor and hold check", self.sql)
        for forbidden in ("payload_json", "row_key_hash", "connection_string", "error_message", "candidate_counts jsonb", "affected_counts jsonb", "cutoffs jsonb"):
            self.assertNotIn(forbidden, self.sql)

    def test_only_required_retention_indexes_are_added(self) -> None:
        indexes = set(re.findall(r"create (?:unique )?index (\w+)", self.sql))
        self.assertEqual(
            {
                "retention_holds_global_active_idx",
                "retention_holds_source_active_idx",
                "sync_runs_retention_idx",
                "schema_change_requests_retention_idx",
                "purge_runs_executable_idx",
            },
            indexes,
        )

    def test_rls_and_least_privilege_contract_are_explicit(self) -> None:
        for table in ("retention_holds", "purge_runs"):
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
            self.assertIn(f"grant select on table public.{table} to service_role", self.sql)
        self.assertNotIn("create policy", self.sql)
        self.assertNotIn("grant delete", self.sql)
        self.assertNotIn("grant all", self.sql)
        self.assertIn("revoke all privileges on function public.guard_purge_run()", self.sql)
        for function in (
            "acquire_retention_locks(uuid)",
            "guard_retention_hold_truncate()",
            "guard_administrative_evidence_truncate()",
        ):
            self.assertIn(f"revoke all privileges on function public.{function}", self.sql)
        self.assertIn("grant select, insert, update on table public.sync_runs to service_role", self.sql)
        self.assertIn("grant select, insert on table public.import_errors to service_role", self.sql)

    def test_current_state_and_its_run_fk_are_untouched(self) -> None:
        self.assertNotIn("alter table public.raw_current_rows", self.sql)
        self.assertNotIn("on delete cascade", self.sql)
        self.assertNotIn("create procedure", self.sql)

    def test_guards_have_no_security_definer_or_dynamic_sql(self) -> None:
        self.assertNotIn("security definer", self.sql)
        self.assertNotIn("execute format", self.sql)
        self.assertNotIn("create procedure", self.sql)

    def test_trigger_surface_covers_delete_and_truncate_guards(self) -> None:
        triggers = set(re.findall(r"create trigger (\w+)", self.sql))
        self.assertEqual(
            {
                "sync_runs_lifecycle_guard",
                "data_sources_hold_lifecycle_guard",
                "data_sources_hold_delete_guard",
                "raw_import_rows_hold_delete_guard",
                "raw_current_rows_hold_delete_guard",
                "import_errors_hold_delete_guard",
                "schema_change_requests_hold_delete_guard",
                "sync_runs_hold_delete_guard",
                "data_sources_hold_truncate_guard",
                "sync_runs_hold_truncate_guard",
                "raw_import_rows_hold_truncate_guard",
                "raw_current_rows_hold_truncate_guard",
                "import_errors_hold_truncate_guard",
                "schema_change_requests_hold_truncate_guard",
                "retention_holds_evidence_truncate_guard",
                "retention_holds_released_immutable_guard",
                "purge_runs_guard",
                "purge_runs_evidence_truncate_guard",
            },
            triggers,
        )

    def test_has_no_destructive_dml_or_secret(self) -> None:
        for token in ("delete from", "truncate public.", "drop table", "drop column"):
            self.assertNotIn(token, self.sql)
        self.assertEqual([], scan_secrets(PATH.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
