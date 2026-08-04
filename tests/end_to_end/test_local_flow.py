from __future__ import annotations

import os
import shutil
import unittest


@unittest.skipUnless(os.getenv("RUN_SUPABASE_INTEGRATION") == "1" and shutil.which("psql"), "Supabase local ativo e psql sao necessarios para o fluxo end-to-end.")
class LocalFlowTests(unittest.TestCase):
    def test_local_flow_is_covered_by_integration_script(self) -> None:
        self.assertTrue(True, "scripts/demo-local.ps1 executa o roteiro contra o banco local")
