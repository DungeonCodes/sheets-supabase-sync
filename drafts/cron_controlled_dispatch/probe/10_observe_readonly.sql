-- Run in observer C, a DIFFERENT backend from A/B. No locking reads.
BEGIN ISOLATION LEVEL READ COMMITTED READ ONLY;
SET LOCAL statement_timeout='5s';
SELECT case_name,claim_count,
 coalesce(claimant_pid<>pg_backend_pid(),false) AS claimed_by_other_backend
 FROM cron_tx_probe.permits ORDER BY case_name;
SELECT r.rolname,r.rolcanlogin,r.rolsuper,r.rolbypassrls,
 has_schema_privilege(r.oid,'cron_tx_probe','USAGE') AS schema_usage,
 has_table_privilege(r.oid,'cron_tx_probe.permits','SELECT') AS permit_read,
 has_table_privilege(r.oid,'cron_tx_probe.permits','UPDATE') AS permit_update,
 has_function_privilege(r.oid,'cron_tx_probe.claim(text)','EXECUTE') AS claim_execute
 FROM pg_roles r WHERE r.rolcanlogin OR r.rolname IN ('anon','authenticated','service_role')
 ORDER BY r.rolname;
ROLLBACK;
