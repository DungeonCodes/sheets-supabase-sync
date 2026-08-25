from __future__ import annotations

import re
import unittest
from pathlib import Path

from sheets_supabase_sync.artifacts import scan_secrets


ROOT = Path(__file__).parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
BASELINE_NAME = "20260804000000_initial_isolated_institution_schema.sql"


class IncrementalRawStateMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = MIGRATIONS / "20260806120000_add_raw_current_state.sql"
        self.assertTrue(self.path.exists())
        self.sql = self.path.read_text(encoding="utf-8").lower()

    def test_migration_is_named_and_ordered_after_the_baseline(self) -> None:
        self.assertRegex(self.path.name, r"^\d{14}_add_raw_current_state\.sql$")
        self.assertGreater(self.path.name[:14], BASELINE_NAME[:14])
        self.assertEqual(4, len(list(MIGRATIONS.glob("*.sql"))))

    def test_migration_has_no_destructive_statement(self) -> None:
        for token in ("drop ", "truncate ", "delete from", "alter column", "rename"):
            self.assertNotIn(token, self.sql)

    def test_migration_only_adds_to_the_applied_history_table(self) -> None:
        alterations = re.findall(r"alter table public\.raw_import_rows\s+(add \w+)", self.sql)
        self.assertEqual({"add column", "add constraint"}, set(alterations))
        self.assertIn("change_type text", self.sql)
        self.assertIn("row_version integer", self.sql)

    def test_current_state_table_and_identity_exist(self) -> None:
        self.assertIn("create table public.raw_current_rows", self.sql)
        self.assertIn("unique (data_source_id, row_key_hash)", self.sql)
        self.assertIn("row_key_hash text not null", self.sql)
        self.assertIn("content_hash text not null", self.sql)
        self.assertIn("payload_json jsonb not null", self.sql)

    def test_foreign_keys_point_only_to_operational_tables(self) -> None:
        references = set(re.findall(r"references\s+public\.([a-z0-9_]+)", self.sql))
        self.assertEqual({"data_sources", "sync_runs"}, references)
        self.assertIn("data_source_id uuid not null references public.data_sources(id)", self.sql)
        self.assertIn("last_sync_run_id uuid references public.sync_runs(id)", self.sql)

    def test_tombstone_and_version_are_declared_with_checks(self) -> None:
        self.assertIn("is_deleted boolean not null default false", self.sql)
        self.assertIn("deleted_at timestamptz", self.sql)
        self.assertIn("version integer not null default 1", self.sql)
        self.assertIn("raw_current_rows_version_positive check (version > 0)", self.sql)
        self.assertIn("(is_deleted and deleted_at is not null) or (not is_deleted and deleted_at is null)", self.sql)
        self.assertIn("source_row_number is null or source_row_number > 0", self.sql)
        self.assertIn("last_seen_at >= first_seen_at", self.sql)

    def test_expected_indexes_exist_without_duplicating_the_unique_constraint(self) -> None:
        indexes = set(re.findall(r"create index (\w+)", self.sql))
        self.assertEqual(
            {"raw_current_rows_active_idx", "raw_current_rows_tombstone_idx", "raw_current_rows_last_run_idx"},
            indexes,
        )
        self.assertIn("where not is_deleted", self.sql)
        self.assertIn("where is_deleted", self.sql)
        self.assertNotIn("create unique index", self.sql)

    def test_row_level_security_is_enabled_and_frontend_has_no_access(self) -> None:
        self.assertIn("alter table public.raw_current_rows enable row level security", self.sql)
        self.assertIn(
            "revoke all privileges on table public.raw_current_rows from public, anon, authenticated, service_role",
            self.sql,
        )
        self.assertNotIn("create policy", self.sql)
        self.assertNotIn("to anon", self.sql)
        self.assertNotIn("to authenticated", self.sql)

    def test_backend_grant_is_exactly_the_minimum_contract(self) -> None:
        grants = re.findall(r"grant ([a-z, ]+) on table public\.raw_current_rows to service_role", self.sql)
        self.assertEqual(["select, insert, update"], [grant.strip() for grant in grants])
        self.assertNotIn("grant all", self.sql)
        self.assertNotIn("grant delete", self.sql)
        self.assertNotIn("grant truncate", self.sql)
        self.assertNotIn("grant references", self.sql)
        self.assertNotIn("grant trigger", self.sql)

    def test_migration_has_no_secret_and_no_multitenant_field(self) -> None:
        self.assertEqual([], scan_secrets(self.path.read_text(encoding="utf-8")))
        for token in ("organization_id", "tenant_id", "postgresql://", "sb_secret_"):
            self.assertNotIn(token, self.sql)


if __name__ == "__main__":
    unittest.main()
