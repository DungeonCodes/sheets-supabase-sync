"""Run only two reviewed PostgreSQL regression tests in the dedicated container."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import runpy
import sys
import unittest
from urllib.parse import quote

import psycopg

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'infra/local-postgres/regression-manifest.json'
PASSWORD_FILE = ROOT / 'runtime/local-postgres-password.txt'
TEST_NAMES = (
    'tests.integration.test_postgres_raw_repository.PostgresRawRepositoryIntegrationTests.test_failures_rollback_every_mutation',
    'tests.integration.test_postgres_raw_repository.PostgresRawRepositoryIntegrationTests.test_commit_ack_loss_is_reconciled_without_retry',
)


def verify_manifest(authorized_hash: str) -> None:
    raw = MANIFEST.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual, authorized_hash.lower()):
        raise RuntimeError('O hash do manifesto não corresponde ao autorizado')
    entries = json.loads(raw)
    old_entries = json.loads((ROOT / 'infra/local-postgres/review-manifest.json').read_bytes())
    required = set(old_entries) | {
        'scripts/run-local-postgres-regression.py',
        'infra/local-postgres/review-manifest.json',
    }
    if set(entries) != required:
        raise RuntimeError('O manifesto não contém o conjunto completo de arquivos')
    for name, expected in entries.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Arquivo alterado: {name}')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--execute-reviewed', action='store_true')
    args = parser.parse_args(argv)
    if not args.execute_reviewed:
        raise RuntimeError('Revisão e autorização humanas são necessárias antes do SQL')
    verify_manifest(args.manifest_sha256)
    existing = runpy.run_path(str(ROOT / 'scripts/run-local-postgres-e2e.py'))
    existing['verify_container']()
    password = PASSWORD_FILE.read_text(encoding='utf-8').strip()
    if len(password) < 32:
        raise RuntimeError('Credencial local ausente ou fraca')
    for name in list(os.environ):
        if name.upper().startswith('PG'):
            del os.environ[name]
    url = f'postgresql://local_admin:{quote(password, safe="")}@127.0.0.1:55432/analytics_fixture'
    with psycopg.connect(url, connect_timeout=5) as connection:
        if connection.execute('select current_database(), current_user, inet_server_port()').fetchone() != ('analytics_fixture', 'local_admin', 5432):
            raise RuntimeError('Banco local não corresponde ao alvo revisado')
    os.environ['LOCAL_DATABASE_URL'] = url
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / 'src'))
    suite = unittest.defaultTestLoader.loadTestsFromNames(TEST_NAMES)
    if suite.countTestCases() != 2:
        raise RuntimeError('Quantidade de testes obrigatórios divergente')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped or result.testsRun != 2:
        raise RuntimeError('Regressão PostgreSQL falhou ou foi pulada')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        detail = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print(f'Falha local: {detail}; detalhes podem conter credenciais.', file=sys.stderr)
        raise SystemExit(1)
