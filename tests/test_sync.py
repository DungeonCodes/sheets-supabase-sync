from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from sheets_supabase_sync.artifacts import scan_secrets
from sheets_supabase_sync.config import SyncConfig
from sheets_supabase_sync.diff import compare
from sheets_supabase_sync.executors import apply_sql_locally, assert_local_url
from sheets_supabase_sync.snapshot import build_snapshot
from sheets_supabase_sync.synchronizer import synchronize
from sheets_supabase_sync.sql_generator import generate_sql


class SyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = SyncConfig("fixture", "id", "mirror_records")
        self.rows = [{"id": "1", "name": "Ana", "score": 10}, {"id": "2", "name": "Bruno", "score": 20}]

    def snapshot(self, rows: list[dict]) -> object:
        return build_snapshot("fixture", rows, "id")

    def test_first_import_and_idempotence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = synchronize(self.rows, self.config, root / "snapshot.json", root / "artifacts")
            second = synchronize(self.rows, self.config, root / "snapshot.json", root / "artifacts2")
            self.assertEqual(2, first["counts"]["new"])
            self.assertEqual(0, second["counts"]["new"] + second["counts"]["changed"])

    def test_missing_snapshot_is_a_first_import(self) -> None:
        result = compare(self.snapshot(self.rows), None)
        self.assertEqual(2, len(result.new))

    def test_new_changed_removed_and_restored(self) -> None:
        old = self.snapshot(self.rows)
        current = self.snapshot([{"id": "1", "name": "Ana Maria", "score": 10}, {"id": "3", "name": "Caio", "score": 5}])
        result = compare(current, old)
        self.assertEqual(["3"], [record.key for record in result.new])
        self.assertEqual(["1"], [record.key for record in result.changed])
        self.assertEqual(["2"], [record.key for record in result.removed])
        restored = compare(old, self.snapshot([{**row, "deleted": True} if row["id"] == "1" else row for row in self.rows]))
        self.assertEqual(["1"], [record.key for record in restored.restored])

    def test_new_line(self) -> None:
        result = compare(self.snapshot([*self.rows, {"id": "3", "name": "Caio", "score": 3}]), self.snapshot(self.rows))
        self.assertEqual(["3"], [row.key for row in result.new])

    def test_changed_line(self) -> None:
        result = compare(self.snapshot([{**self.rows[0], "name": "Ana Maria"}, self.rows[1]]), self.snapshot(self.rows))
        self.assertEqual(["1"], [row.key for row in result.changed])

    def test_removed_line(self) -> None:
        result = compare(self.snapshot([self.rows[0]]), self.snapshot(self.rows))
        self.assertEqual(["2"], [row.key for row in result.removed])

    def test_restored_line(self) -> None:
        previous = self.snapshot([{**self.rows[0], "deleted": True}, self.rows[1]])
        result = compare(self.snapshot(self.rows), previous)
        self.assertEqual(["1"], [row.key for row in result.restored])

    def test_snapshot_tombstone_identifies_restoration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "snapshot.json"
            synchronize(self.rows, self.config, snapshot, root / "initial")
            synchronize([self.rows[0]], self.config, snapshot, root / "removed")
            restored = synchronize(self.rows, self.config, snapshot, root / "restored")
            self.assertEqual(1, restored["counts"]["restored"])

    def test_schema_duplicate_and_type_findings(self) -> None:
        old = self.snapshot(self.rows)
        current = self.snapshot([{"id": "1", "full_name": "Ana", "score": "dez"}, {"id": "2", "full_name": "Ana", "score": "vinte"}])
        result = compare(current, old)
        self.assertIn("full_name", result.new_columns)
        self.assertIn("name", result.missing_columns)
        self.assertIn(("score", "integer", "text"), result.incompatible_types)
        duplicate = self.snapshot([{"id": "1", "name": "Ana"}, {"id": "2", "name": "Ana"}])
        self.assertEqual(["1", "2"], compare(duplicate, None).duplicates)

    def test_new_column(self) -> None:
        result = compare(self.snapshot([{**row, "city": "Sapucaia"} for row in self.rows]), self.snapshot(self.rows))
        self.assertEqual(["city"], result.new_columns)

    def test_missing_column(self) -> None:
        result = compare(self.snapshot([{"id": row["id"], "name": row["name"]} for row in self.rows]), self.snapshot(self.rows))
        self.assertEqual(["score"], result.missing_columns)

    def test_possible_rename(self) -> None:
        result = compare(self.snapshot([{"id": row["id"], "name_full": row["name"], "score": row["score"]} for row in self.rows]), self.snapshot(self.rows))
        self.assertIn(("name", "name_full"), result.possible_renames)

    def test_incompatible_type(self) -> None:
        result = compare(self.snapshot([{**row, "score": "not-a-number"} for row in self.rows]), self.snapshot(self.rows))
        self.assertIn(("score", "integer", "text"), result.incompatible_types)

    def test_duplicate_records(self) -> None:
        duplicate = self.snapshot([{"id": "1", "name": "Ana"}, {"id": "2", "name": "Ana"}])
        self.assertEqual(["1", "2"], compare(duplicate, None).duplicates)

    def test_hostile_value_and_secret_scanner(self) -> None:
        hostile = self.snapshot([{"id": "1", "name": "'); DELETE FROM mirror_records; --"}])
        self.assertEqual(1, len(hostile.records))
        self.assertEqual(["token"], scan_secrets("token=abc123"))
        self.assertEqual([], scan_secrets(json.dumps({"name": "Ana"})))

    def test_artifacts_do_not_contain_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            synchronize(self.rows, self.config, root / "snapshot.json", root / "artifacts")
            combined = "".join(path.read_text(encoding="utf-8") for path in (root / "artifacts").iterdir())
            self.assertEqual([], scan_secrets(combined))

    def test_corrupted_snapshot_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "snapshot.json"
            snapshot.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "corrompido"):
                synchronize(self.rows, self.config, snapshot, root / "artifacts")

    def test_remote_host_refused(self) -> None:
        assert_local_url("http://localhost:54321")
        with self.assertRaises(ValueError):
            assert_local_url("https://project.supabase.co")

    def test_explicit_development_host_is_allowed(self) -> None:
        assert_local_url("postgresql://dev-db:5432/postgres", {"dev-db"})

    def test_sql_is_transactional_and_never_physically_deletes(self) -> None:
        result = compare(self.snapshot([self.rows[0]]), self.snapshot(self.rows))
        sql = generate_sql(result, "mirror_records", "fixture")
        self.assertTrue(sql.startswith("BEGIN;"))
        self.assertTrue(sql.rstrip().endswith("COMMIT;"))
        self.assertNotIn("DELETE FROM", sql)
        self.assertIn("deleted_at = now()", sql)

    def test_executor_uses_one_transaction_without_logging_url(self) -> None:
        captured: dict[str, object] = {}

        def runner(command: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured["command"] = command
            captured["input"] = kwargs["input"]
            return subprocess.CompletedProcess(command, 0, "applied", "")

        result = apply_sql_locally("BEGIN;\nSELECT 1;\nCOMMIT;\n", "postgresql://postgres:postgres@127.0.0.1:54322/postgres", runner=runner)
        self.assertEqual(0, result.returncode)
        self.assertIn("--single-transaction", captured["command"])
        self.assertEqual("SELECT 1;\n", captured["input"])

    def test_executor_reports_rollback_on_failure(self) -> None:
        def failing_runner(command: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 1, "", "error")

        with self.assertRaisesRegex(RuntimeError, "revertida"):
            apply_sql_locally("SELECT 1;", "postgresql://localhost:54322/postgres", runner=failing_runner)

    def test_apply_local_requires_explicit_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "database-url"):
                synchronize(self.rows, self.config, Path(tmp) / "snapshot.json", Path(tmp) / "artifacts", mode="apply-local")

    def test_generate_sql_mode_stays_non_applying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = synchronize(self.rows, self.config, Path(tmp) / "snapshot.json", Path(tmp) / "artifacts", mode="generate-sql")
            self.assertEqual("generate-sql", manifest["mode"])
            self.assertTrue(manifest["dry_run"])

    def test_migration_uses_official_filename_layout(self) -> None:
        migrations = list((Path(__file__).parents[1] / "supabase" / "migrations").glob("*.sql"))
        self.assertEqual(1, len(migrations))
        self.assertRegex(migrations[0].name, r"^\d{14}_[a-z0-9_]+\.sql$")
