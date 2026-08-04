from __future__ import annotations

import os
import time
import unittest

from sheets_supabase_sync.snapshot import build_snapshot


@unittest.skipUnless(os.getenv("RUN_SLOW_TESTS") == "1", "Teste lento; defina RUN_SLOW_TESTS=1.")
class PerformanceTests(unittest.TestCase):
    def test_ten_thousand_rows_baseline(self) -> None:
        rows = [{"id": str(index), "value": index} for index in range(10_000)]
        started = time.perf_counter()
        snapshot = build_snapshot("performance", rows, "id")
        self.assertEqual(10_000, len(snapshot.records))
        self.assertGreater(time.perf_counter() - started, 0)
