from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
PATH = MIGRATIONS / "20260811150000_make_raw_import_event_only.sql"


class EventOnlyMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = PATH.read_text(encoding="utf-8").lower()

    def test_is_exactly_the_third_migration(self) -> None:
        self.assertTrue(PATH.exists())
        self.assertEqual(3, len(list(MIGRATIONS.glob("*.sql"))))
        self.assertEqual(PATH, sorted(MIGRATIONS.glob("*.sql"))[-1])

    def test_replaces_physical_identity_with_logical_event_identity(self) -> None:
        self.assertIn("drop constraint raw_import_rows_run_row_unique", self.sql)
        self.assertIn("unique (sync_run_id, data_source_id, row_key_hash)", self.sql)
        self.assertNotIn("unique (sync_run_id, source_row_number)", self.sql)

    def test_event_contract_is_exact_and_tombstone_has_no_invented_content(self) -> None:
        self.assertIn("change_type in ('insert', 'update', 'tombstone', 'restore')", self.sql)
        self.assertIn("alter column source_row_number drop not null", self.sql)
        self.assertIn("alter column content_hash drop not null", self.sql)
        self.assertIn("alter column payload_json drop not null", self.sql)
        for token in ("source_row_number is null", "content_hash is null", "payload_json is null"):
            self.assertIn(token, self.sql)

    def test_preserves_rls_and_reduces_history_grants(self) -> None:
        self.assertNotIn("disable row level security", self.sql)
        self.assertNotIn("create policy", self.sql)
        self.assertIn("revoke all privileges on table public.raw_import_rows", self.sql)
        self.assertIn("grant select, insert on table public.raw_import_rows to service_role", self.sql)

    def test_has_explicit_empty_table_precondition_and_no_data_deletion(self) -> None:
        self.assertIn("if exists (select 1 from public.raw_import_rows)", self.sql)
        self.assertNotIn("delete from", self.sql)
        self.assertNotIn("truncate", self.sql)
        self.assertNotIn("drop column", self.sql)


if __name__ == "__main__":
    unittest.main()
