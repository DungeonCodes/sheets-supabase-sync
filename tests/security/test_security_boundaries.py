from __future__ import annotations

import unittest

from sheets_supabase_sync.artifacts import scan_secrets
from sheets_supabase_sync.executors import assert_local_url
from sheets_supabase_sync.identifiers import validate_identifier
from sheets_supabase_sync.sql_generator import generate_sql
from sheets_supabase_sync.models import DiffResult, Record


class SecurityBoundaryTests(unittest.TestCase):
    def test_secret_and_hostile_identifiers_are_refused(self) -> None:
        self.assertEqual(["token"], scan_secrets("token=artificial"))
        with self.assertRaises(ValueError):
            validate_identifier("mirror;drop table x")
        with self.assertRaises(ValueError):
            assert_local_url("https://remote.supabase.co")

    def test_hostile_value_remains_data_and_sql_has_no_service_role(self) -> None:
        record = Record("1", {"name": "'); DELETE FROM x; --"}, "hash")
        sql = generate_sql(DiffResult(new=[record]), "mirror_records", "source")
        self.assertIn("raw_data", sql)
        self.assertNotIn("service_role", sql)
