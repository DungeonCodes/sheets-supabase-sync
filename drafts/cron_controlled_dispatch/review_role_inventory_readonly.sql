-- Metadata only. Future authorized inspection, NOT executed in this gate.
BEGIN READ ONLY;
SELECT r.rolname,r.rolcanlogin,r.rolsuper,r.rolbypassrls,
 has_schema_privilege(r.oid,to_regnamespace('vault'),'USAGE') AS vault_usage,
 has_table_privilege(r.oid,to_regclass('vault.decrypted_secrets'),'SELECT') AS vault_select,
 has_any_column_privilege(r.oid,to_regclass('vault.decrypted_secrets'),'SELECT') AS vault_column_select,
 has_schema_privilege(r.oid,to_regnamespace('net'),'USAGE') AS net_usage,
 has_table_privilege(r.oid,to_regclass('net.http_request_queue'),'SELECT') AS queue_select,
 has_any_column_privilege(r.oid,to_regclass('net.http_request_queue'),'SELECT') AS queue_column_select,
 has_table_privilege(r.oid,to_regclass('net.http_request_queue'),'INSERT') AS queue_insert,
 has_table_privilege(r.oid,to_regclass('net.http_request_queue'),'UPDATE') AS queue_update
 FROM pg_roles r WHERE r.rolcanlogin OR r.rolname IN ('anon','authenticated','service_role')
 ORDER BY r.rolname;
SELECT parent.rolname AS granted_role,child.rolname AS member_role,m.admin_option
 FROM pg_auth_members m JOIN pg_roles parent ON parent.oid=m.roleid
 JOIN pg_roles child ON child.oid=m.member ORDER BY 1,2;
SELECT n.nspname,pg_get_userbyid(n.nspowner) AS owner
 FROM pg_namespace n WHERE n.nspname IN ('vault','net','public','cron_dispatch_private');
SELECT n.nspname,c.relname,pg_get_userbyid(c.relowner) AS owner,c.relrowsecurity
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('vault','net','cron_dispatch_private') AND c.relkind IN ('r','p','v');
SELECT p.oid::regprocedure AS routine,pg_get_userbyid(p.proowner) AS owner,p.prosecdef,
 coalesce('search_path=pg_catalog'=ANY(p.proconfig),false) AS fixed_catalog_search_path,
 has_function_privilege('anon',p.oid,'EXECUTE') AS anon_execute,
 has_function_privilege('authenticated',p.oid,'EXECUTE') AS authenticated_execute,
 has_function_privilege('service_role',p.oid,'EXECUTE') AS service_execute
 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname='cron_dispatch_private' OR
  (n.nspname='public' AND p.proname LIKE 'cron_%');
SELECT current_setting('pgrst.db_schemas',true) AS configured_api_schemas_if_visible;
-- NULL above means unknown, not safe. Review Dashboard API settings separately.
ROLLBACK;
