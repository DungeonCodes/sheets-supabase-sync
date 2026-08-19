from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
HISTORY = ROOT / "docs" / "history" / "initial-migrations-poc"
BASELINE = MIGRATIONS / "20260804000000_initial_isolated_institution_schema.sql"
# Digest da baseline aplicada ao staging em 2026-08-05. Ela e imutavel: qualquer
# evolucao deve ocorrer por migration incremental, nunca por edicao deste arquivo.
BASELINE_DIGEST = "35f26438baafe8f5b65bd12ff2136866e7c02d081e6e265fe371a3c676f1a034"


class MigrationBaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = BASELINE.read_text(encoding="utf-8").lower()

    def test_applied_baseline_is_untouched(self) -> None:
        self.assertEqual(BASELINE_DIGEST, hashlib.sha256(BASELINE.read_bytes()).hexdigest())

    def test_baseline_is_the_oldest_migration_and_archives_are_inert(self) -> None:
        active = sorted(path.name for path in MIGRATIONS.glob("*.sql"))
        self.assertEqual(BASELINE.name, active[0])
        self.assertRegex(active[0], r"^\d{14}_initial_isolated_institution_schema\.sql$")
        self.assertEqual(3, len(list(HISTORY.glob("*.sql.txt"))))
        self.assertEqual([], list(HISTORY.glob("*.sql")))

    def test_baseline_has_no_destructive_or_multitenant_sql(self) -> None:
        for token in ("drop ", "truncate ", "delete from", "organization_id", "tenant_id", "create table public.organizations"):
            self.assertNotIn(token, self.baseline)

    def test_operational_tables_and_health_fields_exist(self) -> None:
        for table in ("data_sources", "sync_runs", "raw_import_rows", "import_errors", "schema_change_requests"):
            self.assertIn(f"create table public.{table}", self.baseline)
        for field in ("last_attempt_at", "last_success_at", "last_failure_at", "consecutive_failures", "last_duration_ms", "last_rows_read", "last_rows_inserted", "last_rows_updated", "last_rows_deleted", "last_rows_restored"):
            self.assertIn(field, self.baseline)

    def test_schema_change_request_uses_unambiguous_jsonb_fields(self) -> None:
        self.assertRegex(self.baseline, r"\bprevious_schema\s+jsonb\s+not null")
        self.assertRegex(self.baseline, r"\bproposed_schema\s+jsonb\s+not null")
        self.assertNotRegex(self.baseline, r"\bcurrent_schema\s+jsonb")

        generator = (ROOT / "src" / "sheets_supabase_sync" / "sql_generator.py").read_text(encoding="utf-8")
        self.assertIn("previous_schema, proposed_schema", generator)
        self.assertNotIn("current_schema, proposed_schema", generator)

    def test_foreign_keys_reference_only_operational_tables(self) -> None:
        references = set(re.findall(r"references\s+public\.([a-z0-9_]+)", self.baseline))
        self.assertEqual({"data_sources", "sync_runs"}, references)
        self.assertNotIn("mirror", self.baseline)

    def test_idempotency_constraints_rls_and_restricted_grants_exist(self) -> None:
        self.assertIn("unique (spreadsheet_id, sheet_name)", self.baseline)
        self.assertIn("unique (sync_run_id, source_row_number)", self.baseline)
        self.assertEqual(5, self.baseline.count("enable row level security"))
        self.assertEqual(5, self.baseline.count("revoke all on table"))
        self.assertNotIn("grant all on table public.raw_import_rows to anon", self.baseline)

    def test_seed_is_compatible_and_has_no_secret(self) -> None:
        seed = (ROOT / "supabase" / "seed.sql").read_text(encoding="utf-8").lower()
        self.assertIn("public.data_sources", seed)
        self.assertNotIn("organization_id", seed)
        self.assertNotIn("tenant_id", seed)
        self.assertNotRegex(seed, r"sb_secret_|postgresql://|service_role\s*[:=]")

    def test_history_is_documented(self) -> None:
        self.assertTrue((HISTORY / "README.md").is_file())
