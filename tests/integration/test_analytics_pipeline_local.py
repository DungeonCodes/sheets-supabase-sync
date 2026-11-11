"""Opt-in raw service -> analytical snapshot integration for an isolated local DB."""
from __future__ import annotations

import csv
import os
import unittest
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg

from sheets_supabase_sync.raw_repository import PostgresRawRepository, assess_raw_schema
from sheets_supabase_sync.raw_sync import RawInputRow, RawSyncSource
from sheets_supabase_sync.raw_sync_service import RawSynchronizationService

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.getenv('RUN_ANALYTICS_LOCAL_TESTS') == '1', 'reviewed fixture database required')
class PipelineTests(unittest.TestCase):
    def test_synthetic_lifecycle_from_python_to_analytics(self):
        url = os.environ.get('ANALYTICS_FIXTURE_DATABASE_URL', '')
        parsed = urlparse(url)
        if parsed.scheme not in ('postgres', 'postgresql') or parsed.hostname not in ('127.0.0.1', '::1') or parsed.path != '/analytics_fixture' or parsed.query or parsed.fragment:
            raise RuntimeError('only a dedicated loopback fixture database is allowed')
        suffix = uuid4().hex[:12]
        source = RawSyncSource('fixture_' + suffix, 'fixture_' + suffix, 'synthetic_' + suffix,
                               'Fixture', 'fixture_' + suffix, ('registro_id',))
        schema = '\n'.join(p.read_text(encoding='utf-8') for p in sorted((ROOT / 'supabase/migrations').glob('*.sql')))
        service = RawSynchronizationService(PostgresRawRepository(assess_raw_schema(schema), url))
        with (ROOT / 'data/fixtures/multi_source_b.csv').open(encoding='utf-8', newline='') as file:
            fixtures = list(csv.DictReader(file))
        def sync(values):
            rows = tuple(RawInputRow(index + 2, row) for index, row in enumerate(values))
            return service.persist_locally(source, ('registro_id','categoria','pontuacao'), rows, datetime.now(UTC))
        first = sync(fixtures)
        self.assertEqual(2, first.plan.counts['new'])
        with psycopg.connect(url) as connection:
            source_id = connection.execute('select id from public.data_sources where spreadsheet_id=%s and sheet_name=%s', (source.spreadsheet_id,source.sheet_name)).fetchone()[0]
            source_key = connection.execute('''insert into analytics.dim_source(data_source_id,source_ref,source_name,semantic_contract_version)
                values (%s,%s,%s,%s) returning source_key''', (source_id, 'fixture_dashboard', 'Fonte ficticia', 'category_score_v1')).fetchone()[0]
            connection.execute('''insert into analytics.category_allowlist(source_key,normalized_category,category_label,category_code)
                values (%s,%s,%s,%s),(%s,%s,%s,%s)''', (source_key,'categoria_x','Categoria X','categoria_x',source_key,'categoria_y','Categoria Y','categoria_y'))
        def refresh():
            with psycopg.connect(url) as connection:
                connection.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
                connection.execute('select analytics.refresh_category_score(%s)', (source_id,))
                return connection.execute('select count(*), sum(score_value) from analytics.fact_category_score where source_key=%s and is_current', (source_key,)).fetchone()
        self.assertEqual((2,30), refresh())
        self.assertEqual(2, sync(fixtures).plan.counts['unchanged'])
        self.assertEqual((2,30), refresh())
        changed = [dict(row) for row in fixtures]
        changed[0]['pontuacao'] = '12'
        self.assertEqual(1, sync(changed).plan.counts['changed'])
        self.assertEqual((2,32), refresh())
        self.assertEqual(1, sync(changed[:1]).plan.counts['removed'])
        self.assertEqual((1,12), refresh())
        self.assertEqual(1, sync(changed).plan.counts['restored'])
        self.assertEqual((2,32), refresh())
        print('Synthetic dashboard source_ref: fixture_dashboard')
