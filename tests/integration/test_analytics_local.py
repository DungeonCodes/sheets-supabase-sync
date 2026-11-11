"""Opt-in synthetic PostgreSQL contract checks, only in an isolated fixture DB."""
from __future__ import annotations

import os
import unittest
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb


@unittest.skipUnless(os.getenv('RUN_ANALYTICS_LOCAL_TESTS') == '1', 'local reviewed SQL and fixture database required')
class AnalyticalTransformationTests(unittest.TestCase):
    def setUp(self):
        url = os.environ.get('ANALYTICS_FIXTURE_DATABASE_URL', '')
        parsed = urlparse(url)
        if parsed.scheme not in ('postgres', 'postgresql') or parsed.hostname not in ('127.0.0.1', '::1') or parsed.path != '/analytics_fixture' or parsed.query or parsed.fragment:
            raise RuntimeError('only the isolated local analytics_fixture database is permitted')
        self.connection = psycopg.connect(url)
        self.connection.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        self.source = uuid4()
        suffix = self.source.hex[:12]
        self.connection.execute('''insert into public.data_sources
          (id,name,spreadsheet_id,sheet_name,target_table,business_key)
          values (%s,%s,%s,%s,%s,%s)''',
          (self.source, 'synthetic_' + suffix, 'synthetic_' + suffix, 'fixture', 'fixture_' + suffix, Jsonb(['registro_id'])))
        row = self.connection.execute('''insert into analytics.dim_source
          (data_source_id,source_ref,source_name,semantic_contract_version)
          values (%s,%s,%s,%s) returning source_key''',
          (self.source, 'fixture_' + suffix, 'Fonte ficticia', 'category_score_v1')).fetchone()
        self.source_key = row[0]
        self.connection.execute('''insert into analytics.category_allowlist
          (source_key,normalized_category,category_label,category_code)
          values (%s,%s,%s,%s),(%s,%s,%s,%s)''',
          (self.source_key, 'categoria_x', 'Categoria X', 'categoria_x', self.source_key, 'categoria_y', 'Categoria Y', 'categoria_y'))
        for key, category, score in [('a' * 64, 'categoria_x', '10'), ('b' * 64, 'categoria_y', '20')]:
            self.connection.execute('''insert into public.raw_current_rows
              (data_source_id,row_key_hash,content_hash,payload_json) values (%s,%s,%s,%s)''',
              (self.source, key, 'c' * 64, Jsonb({'categoria':category, 'pontuacao':score})))

    def tearDown(self):
        self.connection.rollback()
        self.connection.close()

    def refresh(self):
        self.connection.execute('select analytics.refresh_category_score(%s)', (self.source,))

    def aggregate(self):
        return self.connection.execute('''select count(*), sum(score_value) from analytics.fact_category_score
          where source_key=%s and is_current''', (self.source_key,)).fetchone()

    def test_snapshot_lifecycle_idempotence_and_rollback(self):
        self.refresh()
        self.assertEqual((2, 30), self.aggregate())
        self.refresh()
        self.assertEqual((2, 30), self.aggregate())
        self.connection.execute('update public.raw_current_rows set payload_json=%s where data_source_id=%s and row_key_hash=%s',
                                (Jsonb({'categoria':'categoria_x','pontuacao':'12'}), self.source, 'a'*64))
        self.refresh()
        self.assertEqual((2, 32), self.aggregate())
        self.connection.execute('update public.raw_current_rows set is_deleted=true, deleted_at=now() where data_source_id=%s and row_key_hash=%s', (self.source, 'b'*64))
        self.refresh()
        self.assertEqual((1, 12), self.aggregate())
        self.connection.execute('update public.raw_current_rows set is_deleted=false, deleted_at=null where data_source_id=%s and row_key_hash=%s', (self.source, 'b'*64))
        self.refresh()
        self.assertEqual((2, 32), self.aggregate())
        with self.assertRaises(psycopg.Error):
            with self.connection.transaction():
                self.connection.execute('update public.raw_current_rows set payload_json=%s where data_source_id=%s and row_key_hash=%s',
                                        (Jsonb({'categoria':'nao_aprovada','pontuacao':'12'}), self.source, 'a'*64))
                self.refresh()
        self.assertEqual((2, 32), self.aggregate())
