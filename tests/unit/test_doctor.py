from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sheets_supabase_sync.doctor import doctor_exit_code, run_doctor
from sheets_supabase_sync.health import HealthStatus


class DoctorTests(unittest.TestCase):
    def test_doctor_ok_and_warning_exit_code(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "config.json"
            config.write_text("{}", encoding="utf-8")
            migrations = root / "migrations"
            migrations.mkdir()
            (migrations / "20260803000000_test.sql").write_text("select 1;", encoding="utf-8")
            checks = run_doctor(config, root / "runtime", migrations)
            self.assertEqual(1, doctor_exit_code(checks))
            self.assertIn(HealthStatus.WARNING, [check.status for check in checks])

    def test_doctor_failure_for_missing_config(self) -> None:
        with TemporaryDirectory() as temp:
            root = Path(temp)
            checks = run_doctor(root / "missing.json", root / "runtime", root / "migrations")
            self.assertEqual(2, doctor_exit_code(checks))
