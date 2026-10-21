-- DRAFT. Separate administrative approval required; never run in this gate.
BEGIN;
DO $review$
BEGIN
 RAISE EXCEPTION 'inactive_preparation_review_blocked_see_review_md';
 IF current_setting('app.cron_sql_review', true) IS DISTINCT FROM 'staging-reviewed' OR current_user <> 'postgres' THEN
   RAISE EXCEPTION 'draft_requires_staging_sql_review';
 END IF;
 IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname='supabase_vault') THEN
   RAISE EXCEPTION 'existing_vault_required';
 END IF;
 IF current_setting('server_version_num')::integer < 140000 THEN
   RAISE EXCEPTION 'postgres_version_requires_review';
 END IF;
END $review$;
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;
-- Deliberately do not install http: version 1.6 forces redirects.
DO $versions$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_cron' AND extversion='1.6.4')
 OR NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname='pg_net' AND extversion='0.20.4') THEN
   RAISE EXCEPTION 'extension_version_requires_review';
 END IF;
END $versions$;
COMMIT;
