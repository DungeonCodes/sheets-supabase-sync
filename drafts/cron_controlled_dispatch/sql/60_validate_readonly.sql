-- DRAFT POST-INSTALL/POST-TEST validation. No raw bodies, tokens or job commands.
BEGIN READ ONLY;
SELECT a.authorization_id,a.ref,a.expected_sha,a.job_id,j.active,
 a.enqueue_count,a.claim_count,a.outcome,a.net_request_id,a.cron_backend_pid,
 a.enqueued_at,a.consumed_at,a.completed_at,a.http_status,a.github_run_id,
 CASE WHEN a.claim_xid IS NULL THEN NULL ELSE pg_xact_status(a.claim_xid) END AS claim_transaction_status
 FROM cron_dispatch_private.authorizations a LEFT JOIN cron.job j ON j.jobid=a.job_id;
SELECT d.jobid,d.runid,d.job_pid,d.status,d.start_time,d.end_time
 FROM cron.job_run_details d JOIN cron_dispatch_private.authorizations a ON a.job_id=d.jobid
 ORDER BY d.start_time;
SELECT r.id,r.status_code,r.timed_out,r.created
 FROM net._http_response r JOIN cron_dispatch_private.authorizations a ON a.net_request_id=r.id;
SELECT role_name,
 has_schema_privilege(role_name,'cron_dispatch_private','USAGE') AS private_usage,
 has_table_privilege(role_name,'vault.decrypted_secrets','SELECT') AS vault_read,
 has_table_privilege(role_name,'net.http_request_queue','SELECT') AS queue_read,
 has_function_privilege(role_name,'public.cron_claim_dispatch(uuid)','EXECUTE') AS claim_execute
 FROM unnest(ARRAY['anon','authenticated','service_role']) AS role_name;
SELECT (SELECT count(*) FROM public.sync_runs) AS sync_runs,
 (SELECT count(*) FROM public.raw_import_rows) AS raw_import_rows,
 (SELECT count(*) FROM public.raw_current_rows) AS raw_current_rows;
-- Scope reconciliation of counters/events/source state to the reviewed demo
-- using the existing application configuration, without selecting payload_json.
ROLLBACK;
