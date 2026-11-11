"""Apply a reviewed local-only package once, then require real DB and browser tests."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import unittest
from urllib.parse import quote

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'infra/local-postgres/review-manifest.json'
PASSWORD_FILE = ROOT / 'runtime/local-postgres-password.txt'
READER_PASSWORD_FILE = ROOT / 'runtime/local-dashboard-password.txt'
SQL_FILES = [
    'infra/local-postgres/01_compat_roles.sql',
    *[str(p.relative_to(ROOT)).replace('\\', '/') for p in sorted((ROOT / 'supabase/migrations').glob('*.sql'))],
    'supabase/seed.sql', 'infra/local-postgres/02_dashboard_rls.sql',
]
TESTS = (
    'tests.integration.test_postgres_raw_repository',
    'tests.integration.test_operational_postgres',
    'tests.integration.test_analytics_local',
    'tests.integration.test_analytics_pipeline_local',
    'tests.integration.test_dashboard_access_local',
)


def verify_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for relative, expected in manifest.items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Arquivo revisado alterado: {relative}')
    if not set(SQL_FILES).issubset(manifest):
        raise RuntimeError('Manifesto não cobre todos os arquivos SQL')


def verify_container() -> None:
    result = subprocess.run(['docker', 'inspect', 'sheets-sync-local-postgres'], capture_output=True, check=True, text=True)
    container = json.loads(result.stdout)[0]
    labels = container['Config'].get('Labels') or {}
    bindings = container['NetworkSettings']['Ports'].get('5432/tcp') or []
    mounts = container.get('Mounts') or []
    if (labels.get('com.docker.compose.project') != 'sheets-sync-local-pg'
        or container['Config']['Image'] != 'postgres:17.11-alpine3.23'
        or container['State'].get('Health', {}).get('Status') != 'healthy'
        or bindings != [{'HostIp': '127.0.0.1', 'HostPort': '55432'}]
        or not any(m.get('Name') == 'sheets-sync-local-pg-data' and m.get('Destination') == '/var/lib/postgresql/data' for m in mounts)):
        raise RuntimeError('Contêiner ou porta local divergem da configuração revisada')


def execute_package(admin_url: str, reader_password: str) -> None:
    with psycopg.connect(admin_url, connect_timeout=5) as connection:
        current = connection.execute('select current_database(), current_user, inet_server_port()').fetchone()
        if current != ('analytics_fixture', 'local_admin', 5432):
            raise RuntimeError('Banco dedicado não corresponde ao esperado')
        if connection.execute("select to_regclass('public.data_sources')").fetchone()[0] is not None:
            raise RuntimeError('Banco não está vazio; não reaplicar automaticamente')
        for relative in SQL_FILES:
            connection.execute((ROOT / relative).read_text(encoding='utf-8'), prepare=False)
        connection.execute(sql.SQL('ALTER ROLE dashboard_fixture PASSWORD {}').format(sql.Literal(reader_password)))
    print('Pacote SQL aplicado na transação local dedicada.')


def run_tests(admin_url: str, reader_url: str, token: str) -> None:
    os.environ.update({
        'LOCAL_DATABASE_URL': admin_url, 'ANALYTICS_FIXTURE_DATABASE_URL': admin_url,
        'RUN_SUPABASE_INTEGRATION': '1', 'RUN_ANALYTICS_LOCAL_TESTS': '1',
        'DASHBOARD_DATABASE_URL': reader_url, 'DASHBOARD_SOURCE_REF': 'fixture_dashboard',
        'DASHBOARD_ACCESS_TOKEN': token, 'DASHBOARD_MODE': 'postgres',
    })
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / 'src'))
    suite = unittest.defaultTestLoader.loadTestsFromNames(TESTS)
    if suite.countTestCases() != 12:
        raise RuntimeError('Quantidade de testes obrigatórios divergente')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped or result.testsRun != 12:
        raise RuntimeError('Testes PostgreSQL falharam ou foram pulados')
    browser_env = os.environ.copy()
    browser_env.pop('LOCAL_DATABASE_URL', None)
    browser_env.pop('ANALYTICS_FIXTURE_DATABASE_URL', None)
    browser = subprocess.run([str(ROOT / 'apps/dashboard/node_modules/.bin/playwright.cmd'), 'test', '--config', 'playwright.pg.config.ts', '--reporter=json'],
                             cwd=ROOT / 'apps/dashboard', env=browser_env, capture_output=True, text=True)
    if browser.returncode:
        raise RuntimeError('Teste do navegador falhou; execute diagnóstico local sem expor segredos')
    report = json.loads(browser.stdout)
    stats = report['stats']
    if stats['expected'] != 1 or stats['unexpected'] != 0 or stats['skipped'] != 0:
        raise RuntimeError('Teste do navegador ausente, falhou ou foi pulado')
    print('Teste Playwright PostgreSQL passou.')


def main() -> int:
    if sys.argv[1:] != ['--execute-reviewed']:
        print('Requer revisão humana e --execute-reviewed; nenhum SQL executado.')
        return 1
    verify_manifest()
    verify_container()
    if READER_PASSWORD_FILE.exists():
        raise RuntimeError('Credencial do leitor já existe; preserve o estado e investigue')
    admin_password = PASSWORD_FILE.read_text(encoding='utf-8').strip()
    if len(admin_password) < 32:
        raise RuntimeError('Credencial local ausente ou fraca')
    reader_password = secrets.token_urlsafe(32)
    token = secrets.token_urlsafe(32)
    admin_url = f'postgresql://local_admin:{quote(admin_password, safe="")}@127.0.0.1:55432/analytics_fixture'
    reader_url = f'postgresql://dashboard_fixture:{quote(reader_password, safe="")}@127.0.0.1:55432/analytics_fixture'
    execute_package(admin_url, reader_password)
    READER_PASSWORD_FILE.write_text(reader_password, encoding='utf-8')
    run_tests(admin_url, reader_url, token)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        detail = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print(f'Falha local: {detail}; diagnóstico detalhado pode conter credenciais.', file=sys.stderr)
        raise SystemExit(1)
