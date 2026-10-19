-- DRAFT REVIEW QUERY. No decrypted secrets, request headers or raw job commands.
BEGIN READ ONLY;
SELECT current_user, current_setting('transaction_read_only') AS read_only;
SELECT name, default_version, installed_version FROM pg_available_extensions
 WHERE name IN ('pg_cron', 'pg_net', 'http', 'supabase_vault');
SELECT name, setting FROM pg_settings
 WHERE name IN ('cron.use_background_workers', 'cron.log_run', 'pg_net.ttl');
SELECT role_name,
       has_schema_privilege(role_name, 'vault', 'USAGE') AS vault_usage,
       has_table_privilege(role_name, 'vault.decrypted_secrets', 'SELECT') AS vault_read
 FROM unnest(ARRAY['postgres','service_role','anon','authenticated']) AS role_name;
SELECT count(*) AS vault_secret_count FROM vault.secrets;
-- Flag existing public privileged wrappers without printing their definitions.
SELECT p.oid::regprocedure AS privileged_wrapper,
 pg_get_userbyid(p.proowner) AS owner,
 has_function_privilege('anon',p.oid,'EXECUTE') AS anon_execute,
 has_function_privilege('authenticated',p.oid,'EXECUTE') AS authenticated_execute,
 has_function_privilege('service_role',p.oid,'EXECUTE') AS service_execute
 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname='public' AND p.prosecdef AND p.prosrc ILIKE '%vault%';
SELECT to_regclass('cron.job') IS NOT NULL AS cron_catalog_exists,
       to_regclass('net.http_request_queue') IS NOT NULL AS net_catalog_exists;
SELECT (SELECT count(*) FROM public.sync_runs) AS sync_runs,
       (SELECT count(*) FROM public.raw_import_rows) AS raw_import_rows,
       (SELECT count(*) FROM public.raw_current_rows) AS raw_current_rows;
ROLLBACK;
