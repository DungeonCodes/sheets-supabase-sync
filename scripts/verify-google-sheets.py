from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from time import monotonic

from sheets_supabase_sync.errors import SyncError
from sheets_supabase_sync.google_config import load_google_sheets_config
from sheets_supabase_sync.google_sheets import GoogleSheetsReader, validate_fictitious_fixture
from sheets_supabase_sync.google_transport import GoogleHttpTransport


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostico somente leitura e sanitizado da fixture Google Sheets.")
    parser.add_argument("--confirm-fictitious", action="store_true", help="Confirma revisao humana de que a planilha contem somente dados ficticios.")
    args = parser.parse_args()
    if not args.confirm_fictitious:
        print("[PULADO] leitura real exige --confirm-fictitious apos revisao humana da fixture")
        return 3
    root = Path(__file__).parents[1]
    started = monotonic()
    try:
        config = load_google_sheets_config(root)
        transport = GoogleHttpTransport(config.credential_file)
        reader = GoogleSheetsReader(transport, retry_policy=config.retry_policy, timeout_seconds=config.timeout_seconds)
        result = reader.read(config.spreadsheet_id, config.sheet_name, config.optional_range)
        validate_fictitious_fixture(result)
    except SyncError as error:
        print(f"[FALHA] categoria={error.code.value}; nenhum segredo ou conteudo foi exibido")
        return 2
    except Exception:
        logging.getLogger(__name__).exception("Falha interna sanitizada", exc_info=False)
        print("[FALHA] categoria=internal; nenhum segredo ou conteudo foi exibido")
        return 2
    duration_ms = round((monotonic() - started) * 1000)
    print("[OK] autenticacao_aprovada=true")
    print("[OK] planilha_acessivel=true")
    print("[OK] aba_encontrada=true")
    print(f"[OK] abas={result.sheet_count}; colunas={len(result.header)}; linhas={len(result.rows)}")
    print(f"[OK] linhas_vazias_ignoradas={result.empty_rows_ignored}; retries={result.retry_count}; duracao_ms={duration_ms}")
    print("[OK] modo=read_only; dados_ficticios_confirmados=true; conteudo_exibido=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
