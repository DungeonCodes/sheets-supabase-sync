"""PostgreSQL role checks for the dedicated synthetic local database."""
import os
import unittest
from uuid import uuid4

import psycopg


class DashboardAccessTests(unittest.TestCase):
    def test_reader_is_restricted_to_the_fixture_source(self):
        admin_url = os.environ['ANALYTICS_FIXTURE_DATABASE_URL']
        reader_url = os.environ['DASHBOARD_DATABASE_URL']
        suffix = uuid4().hex[:12]
        with psycopg.connect(admin_url) as admin:
            source_id = admin.execute(
                "insert into public.data_sources(name,spreadsheet_id,sheet_name,target_table,business_key) "
                "values (%s,%s,'Fixture',%s,'[\"id\"]'::jsonb) returning id",
                ('other_' + suffix, 'other_' + suffix, 'other_' + suffix),
            ).fetchone()[0]
            admin.execute(
                "insert into analytics.dim_source(data_source_id,source_ref,source_name,semantic_contract_version) "
                "values (%s,%s,'Other fixture','category_score_v1')",
                (source_id, 'other_' + suffix),
            )
        with psycopg.connect(reader_url) as reader:
            self.assertEqual('dashboard_fixture', reader.execute('select current_user').fetchone()[0])
            refs = reader.execute('select source_ref from analytics.dim_source').fetchall()
            self.assertEqual([('fixture_dashboard',)], refs)
            self.assertEqual(0, reader.execute('select count(*) from public.data_sources where id=%s', (source_id,)).fetchone()[0])
            flags = reader.execute(
                "select rolsuper, rolbypassrls, rolcreatedb, rolcreaterole from pg_roles where rolname=current_user"
            ).fetchone()
            self.assertEqual((False, False, False, False), flags)
            privileges = reader.execute(
                "select has_table_privilege(current_user, 'analytics.fact_category_score', 'INSERT'), "
                "has_table_privilege(current_user, 'analytics.fact_category_score', 'UPDATE'), "
                "has_table_privilege(current_user, 'analytics.fact_category_score', 'DELETE'), "
                "has_database_privilege(current_user, current_database(), 'CREATE')"
            ).fetchone()
            self.assertEqual((False, False, False, False), privileges)
            for statement in (
                'select payload_json from public.raw_current_rows',
                'update analytics.fact_category_score set is_current=false',
                "insert into analytics.dim_source(data_source_id,source_ref,source_name,semantic_contract_version) "
                "values (gen_random_uuid(),'forbidden','Forbidden','category_score_v1')",
                'select analytics.refresh_category_score(gen_random_uuid())',
                'create table public.forbidden_fixture(id integer)',
            ):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with reader.transaction():
                        reader.execute(statement)
