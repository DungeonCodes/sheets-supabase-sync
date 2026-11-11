-- Escopo local fixo; não usar como política de produção ou multi-tenant.
DO $$ BEGIN
  IF current_database() <> 'analytics_fixture' THEN
    RAISE EXCEPTION 'wrong database';
  END IF;
END $$;
REVOKE TEMPORARY ON DATABASE analytics_fixture FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA analytics FROM dashboard_fixture;
GRANT USAGE ON SCHEMA analytics TO dashboard_fixture;
GRANT USAGE ON SCHEMA public TO dashboard_fixture;
GRANT SELECT ON analytics.dim_source, analytics.dim_category, analytics.fact_category_score TO dashboard_fixture;
GRANT SELECT (id, enabled, last_success_at, consecutive_failures) ON public.data_sources TO dashboard_fixture;
GRANT SELECT (data_source_id, status, started_at, finished_at) ON public.sync_runs TO dashboard_fixture;
REVOKE ALL ON public.raw_current_rows, public.raw_import_rows FROM PUBLIC, dashboard_fixture;
CREATE POLICY fixture_source_read ON analytics.dim_source FOR SELECT TO dashboard_fixture
  USING (source_ref = 'fixture_dashboard');
CREATE POLICY fixture_category_read ON analytics.dim_category FOR SELECT TO dashboard_fixture
  USING (EXISTS (SELECT 1 FROM analytics.dim_source d WHERE d.source_key = dim_category.source_key AND d.source_ref = 'fixture_dashboard'));
CREATE POLICY fixture_fact_read ON analytics.fact_category_score FOR SELECT TO dashboard_fixture
  USING (EXISTS (SELECT 1 FROM analytics.dim_source d WHERE d.source_key = fact_category_score.source_key AND d.source_ref = 'fixture_dashboard'));
CREATE POLICY fixture_data_source_read ON public.data_sources FOR SELECT TO dashboard_fixture
  USING (EXISTS (SELECT 1 FROM analytics.dim_source d WHERE d.data_source_id = data_sources.id AND d.source_ref = 'fixture_dashboard'));
CREATE POLICY fixture_run_read ON public.sync_runs FOR SELECT TO dashboard_fixture
  USING (EXISTS (SELECT 1 FROM analytics.dim_source d WHERE d.data_source_id = sync_runs.data_source_id AND d.source_ref = 'fixture_dashboard'));
