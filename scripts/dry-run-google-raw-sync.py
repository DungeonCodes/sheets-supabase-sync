from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sheets_supabase_sync.google_config import load_google_sheets_config
from sheets_supabase_sync.google_sheets import GoogleSheetsReader, validate_fictitious_fixture
from sheets_supabase_sync.google_transport import GoogleHttpTransport
from sheets_supabase_sync.raw_sync import RawInputRow, RawSyncSource
from sheets_supabase_sync.raw_sync_service import RawSynchronizationService


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run Google Sheets para plano raw, sem acesso ao Supabase.")
    parser.add_argument("--confirm-fictitious", action="store_true")
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--target-table", required=True)
    parser.add_argument("--business-key", required=True)
    args = parser.parse_args()
    if not args.confirm_fictitious:
        print("[PULADO] requer --confirm-fictitious")
        return 3
    root = Path(__file__).parents[1]
    try:
        config = load_google_sheets_config(root)
        sheet = GoogleSheetsReader(GoogleHttpTransport(config.credential_file), retry_policy=config.retry_policy, timeout_seconds=config.timeout_seconds).read(
            config.spreadsheet_id, config.sheet_name, config.optional_range
        )
        validate_fictitious_fixture(sheet)
        source = RawSyncSource(
            logical_name=args.source_name,
            source_hash=sheet.source_hash,
            spreadsheet_id=config.spreadsheet_id,
            sheet_name=config.sheet_name,
            target_table=args.target_table,
            business_key=(args.business_key,),
        )
        rows = tuple(
            RawInputRow(row.source_row_number, dict(zip(sheet.normalized_header, row.values, strict=True)))
            for row in sheet.rows
        )
        result = RawSynchronizationService().dry_run(source, sheet.normalized_header, rows, sheet.read_at, duration_ms=sheet.duration_ms)
    except Exception as error:
        from sheets_supabase_sync.errors import SyncError

        category = error.code.value if isinstance(error, SyncError) else "internal"
        print(f"[FALHA] categoria={category}; nenhum dado foi persistido")
        return 2
    counts = result.plan.counts
    print(f"[OK] fonte_hash={source.source_hash[:12]}; snapshot_hash={result.plan.snapshot.snapshot_hash[:12]}")
    print(f"[OK] linhas_lidas={result.metrics.rows_read}; novas={counts['new']}; alteradas={counts['changed']}; removidas={counts['removed']}; restauradas={counts['restored']}; inalteradas={counts['unchanged']}")
    print(f"[OK] persistidas={result.metrics.rows_persisted}; duracao_ms={result.metrics.duration_ms}; modo=dry_run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
