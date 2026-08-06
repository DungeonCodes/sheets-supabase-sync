from __future__ import annotations

import os
import unittest
from pathlib import Path

from sheets_supabase_sync.google_config import load_google_sheets_config
from sheets_supabase_sync.google_sheets import GoogleSheetsReader, validate_fictitious_fixture
from sheets_supabase_sync.google_transport import GoogleHttpTransport


@unittest.skipUnless(
    os.environ.get("RUN_GOOGLE_SHEETS_INTEGRATION") == "1" and os.environ.get("GOOGLE_TEST_DATA_CONFIRMED_FICTITIOUS") == "1",
    "requer fixture privada configurada e confirmacao humana de dados ficticios",
)
class GoogleSheetsRealIntegrationTests(unittest.TestCase):
    def test_reads_private_fictitious_sheet_without_exposing_cells(self) -> None:
        root = Path(__file__).parents[2]
        config = load_google_sheets_config(root)
        result = GoogleSheetsReader(
            GoogleHttpTransport(config.credential_file),
            retry_policy=config.retry_policy,
            timeout_seconds=config.timeout_seconds,
        ).read(config.spreadsheet_id, config.sheet_name, config.optional_range)
        validate_fictitious_fixture(result)
        self.assertGreater(len(result.header), 0)
        self.assertGreaterEqual(len(result.rows), 1)


if __name__ == "__main__":
    unittest.main()
