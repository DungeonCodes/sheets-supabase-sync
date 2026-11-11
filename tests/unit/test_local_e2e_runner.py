"""Offline checks for the local E2E fail-closed boundary."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('local_e2e_runner', ROOT / 'scripts/run-local-postgres-e2e.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class LocalRunnerTests(unittest.TestCase):
    def test_requires_explicit_execution_flag(self):
        with patch.object(runner.sys, 'argv', ['runner']), patch.object(runner, 'execute_package') as execute:
            self.assertEqual(1, runner.main())
            execute.assert_not_called()

    def test_rejects_container_bound_to_all_interfaces(self):
        fake = [{
            'Config': {'Image': 'postgres:17.11-alpine3.23', 'Labels': {'com.docker.compose.project': 'sheets-sync-local-pg'}},
            'State': {'Health': {'Status': 'healthy'}},
            'NetworkSettings': {'Ports': {'5432/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '55432'}]}},
            'Mounts': [{'Name': 'sheets-sync-local-pg-data', 'Destination': '/var/lib/postgresql/data'}],
        }]
        with patch.object(runner.subprocess, 'run', return_value=SimpleNamespace(stdout=json.dumps(fake))):
            with self.assertRaises(RuntimeError):
                runner.verify_container()

    def test_required_test_skip_is_failure(self):
        suite = SimpleNamespace(countTestCases=lambda: 12)
        result = SimpleNamespace(wasSuccessful=lambda: True, skipped=[('test', 'reason')], testsRun=12)
        with patch.dict(runner.os.environ, {}), \
             patch.object(runner.unittest.defaultTestLoader, 'loadTestsFromNames', return_value=suite), \
             patch.object(runner.unittest, 'TextTestRunner', return_value=SimpleNamespace(run=lambda _: result)), \
             patch.object(runner.subprocess, 'run') as browser:
            with self.assertRaises(RuntimeError):
                runner.run_tests('unused', 'unused', 'synthetic-token')
            browser.assert_not_called()

    def test_missing_or_changed_manifest_is_failure(self):
        with patch.object(runner, 'MANIFEST', ROOT / 'missing-review-manifest.json'):
            with self.assertRaises(FileNotFoundError):
                runner.verify_manifest()
