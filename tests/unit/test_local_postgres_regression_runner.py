"""Offline guard tests for the two-test local regression runner."""
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('regression_runner', ROOT / 'scripts/run-local-postgres-regression.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RegressionRunnerTests(unittest.TestCase):
    def test_without_approval_it_does_not_reach_database(self):
        with patch.object(runner.psycopg, 'connect') as connect:
            with self.assertRaises(RuntimeError):
                runner.main(['--manifest-sha256', '0' * 64])
            connect.assert_not_called()

    def test_invalid_manifest_digest_fails_before_database(self):
        with patch.object(runner.psycopg, 'connect') as connect:
            with self.assertRaises(RuntimeError):
                runner.main(['--manifest-sha256', '0' * 64, '--execute-reviewed'])
            connect.assert_not_called()

    def test_only_two_named_tests_are_selected(self):
        self.assertEqual(2, len(runner.TEST_NAMES))
        self.assertTrue(all(name.startswith('tests.integration.test_postgres_raw_repository.') for name in runner.TEST_NAMES))

    def test_skipped_test_is_not_success(self):
        suite = SimpleNamespace(countTestCases=lambda: 2)
        result = SimpleNamespace(wasSuccessful=lambda: True, skipped=[('test', 'reason')], testsRun=2)
        connection = SimpleNamespace(execute=lambda _: SimpleNamespace(fetchone=lambda: ('analytics_fixture', 'local_admin', 5432)))
        class ConnectionContext:
            def __enter__(self):
                return connection
            def __exit__(self, *args):
                return None
        with patch.object(runner, 'verify_manifest'), patch.object(runner.runpy, 'run_path', return_value={'verify_container': lambda: None}), \
             patch.object(runner.PASSWORD_FILE.__class__, 'read_text', return_value='x' * 32), \
             patch.object(runner.psycopg, 'connect', return_value=ConnectionContext()), \
             patch.object(runner.unittest.defaultTestLoader, 'loadTestsFromNames', return_value=suite), \
             patch.object(runner.unittest, 'TextTestRunner', return_value=SimpleNamespace(run=lambda _: result)), \
             patch.dict(runner.os.environ, {}):
            with self.assertRaises(RuntimeError):
                runner.main(['--manifest-sha256', '0' * 64, '--execute-reviewed'])
