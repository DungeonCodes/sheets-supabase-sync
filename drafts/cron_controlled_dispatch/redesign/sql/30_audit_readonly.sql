-- Future inspection only. NULL exposed-schema config means unknown, not safe.
BEGIN READ ONLY;
SELECT r.rolname,r.rolcanlogin,r.rolsuper,r.rolbypassrls,
 has_schema_privilege(r.oid,to_regnamespace('cron_dispatch_v2'),'USAGE') AS schema_usage,
 has_table_privilege(r.oid,to_regclass('cron_dispatch_v2.permits'),'SELECT') AS ledger_read,
 has_table_privilege(r.oid,to_regclass('cron_dispatch_v2.permits'),'UPDATE') AS ledger_write
 FROM pg_roles r WHERE r.rolcanlogin OR r.rolname IN
 ('cron_dispatch_owner_v2','cron_dispatch_edge_v2','anon','authenticated','service_role');
SELECT p.oid::regprocedure,pg_get_userbyid(p.proowner) AS owner,p.prosecdef,
 coalesce('search_path=pg_catalog'=ANY(p.proconfig),false) AS safe_search_path,
 has_function_privilege('cron_dispatch_edge_v2',p.oid,'EXECUTE') AS edge_execute
 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='cron_dispatch_v2';
SELECT current_setting('pgrst.db_schemas',true) AS api_schemas_if_visible;
ROLLBACK;
