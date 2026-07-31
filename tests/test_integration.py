from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from sheets_supabase_sync.config import SyncConfig
from sheets_supabase_sync.synchronizer import synchronize


ROOT = Path(__file__).parents[1]
DATABASE_URL = os.getenv("LOCAL_DATABASE_URL")


@unittest.skipUnless(os.getenv("RUN_SUPABASE_INTEGRATION") == "1" and shutil.which("supabase") and DATABASE_URL, "Supabase local indisponivel; execute scripts/test-integration.ps1 com o ambiente ativo.")
class SupabaseIntegrationTests(unittest.TestCase):
    def test_migrations_are_visible_locally(self) -> None:
        result = subprocess.run(["supabase", "migration", "list", "--workdir", str(ROOT)], text=True, capture_output=True, check=False)
        self.assertEqual(0, result.returncode, result.stderr)

    @unittest.skipUnless(shutil.which("psql"), "psql indisponivel; necessario para aplicar SQL no banco local.")
    def test_apply_reapply_change_remove_and_restore(self) -> None:
        config = SyncConfig("integration_fixture", "id", "mirror_records")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "snapshot.json"
            artifact = root / "artifacts"
            first = synchronize([{"id": "1", "name": "Ana"}, {"id": "2", "name": "Bruno"}], config, snapshot, artifact / "first", "apply-local", DATABASE_URL)
            again = synchronize([{"id": "1", "name": "Ana"}, {"id": "2", "name": "Bruno"}], config, snapshot, artifact / "again", "apply-local", DATABASE_URL)
            changed = synchronize([{"id": "1", "name": "Ana Maria"}, {"id": "2", "name": "Bruno"}], config, snapshot, artifact / "changed", "apply-local", DATABASE_URL)
            removed = synchronize([{"id": "1", "name": "Ana Maria"}], config, snapshot, artifact / "removed", "apply-local", DATABASE_URL)
            restored = synchronize([{"id": "1", "name": "Ana Maria"}, {"id": "2", "name": "Bruno"}], config, snapshot, artifact / "restored", "apply-local", DATABASE_URL)
        self.assertEqual(2, first["counts"]["new"])
        self.assertEqual(0, again["counts"]["new"] + again["counts"]["changed"])
        self.assertEqual(1, changed["counts"]["changed"])
        self.assertEqual(1, removed["counts"]["removed"])
        self.assertEqual(1, restored["counts"]["new"])
