-- DRAFT. A THIRD, explicit approval for one Cron test is mandatory.
-- Not part of installation approval. Never run automatically with other files.
BEGIN;
DO $arm$
DECLARE
 permit uuid := nullif(current_setting('app.cron_authorization_id',true),'')::uuid;
 probe uuid := nullif(current_setting('app.cron_probe_id',true),'')::uuid;
 a cron_dispatch_private.authorizations%ROWTYPE;
 role_name text;
BEGIN
 RAISE EXCEPTION 'inactive_preparation_review_blocked_see_review_md';
 IF current_setting('app.cron_activation_review',true) IS DISTINCT FROM 'one-cron-test-reviewed'
 OR current_user<>'postgres' THEN RAISE EXCEPTION 'single_test_approval_required'; END IF;
 SELECT * INTO a FROM cron_dispatch_private.authorizations WHERE authorization_id=permit FOR UPDATE;
 IF NOT FOUND OR a.outcome<>'armed' OR a.enqueue_count<>0 OR a.claim_count<>0
 OR clock_timestamp()>=a.expires_at THEN RAISE EXCEPTION 'authorization_not_armable'; END IF;
 IF probe IS NULL OR NOT public.cron_check_commit_probe(probe) THEN
   RAISE EXCEPTION 'separate_rpc_commit_probe_required';
 END IF;
 IF (SELECT count(*) FROM vault.secrets WHERE name='cron_dispatch_edge_trigger')<>1 THEN
   RAISE EXCEPTION 'dedicated_trigger_credential_missing';
 END IF;
 FOREACH role_name IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
   IF has_table_privilege(role_name,'vault.decrypted_secrets','SELECT')
   OR has_any_column_privilege(role_name,'vault.decrypted_secrets','SELECT')
   OR has_schema_privilege(role_name,'vault','USAGE')
   OR has_table_privilege(role_name,'net.http_request_queue','SELECT')
   OR has_any_column_privilege(role_name,'net.http_request_queue','SELECT')
   OR has_schema_privilege(role_name,'cron_dispatch_private','USAGE') THEN
     RAISE EXCEPTION 'effective_privileges_unsafe';
   END IF;
 END LOOP;
 FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
   IF has_function_privilege(role_name,'public.cron_claim_dispatch(uuid)','EXECUTE')
   OR has_function_privilege(role_name,'public.cron_confirm_dispatch_claim(uuid,uuid)','EXECUTE')
   OR has_function_privilege(role_name,'public.cron_finish_dispatch(uuid,uuid,text,integer,bigint)','EXECUTE') THEN
     RAISE EXCEPTION 'effective_rpc_execute_unsafe';
   END IF;
 END LOOP;
 IF EXISTS (SELECT 1 FROM cron.job WHERE active) THEN
   RAISE EXCEPTION 'concurrent_cron_job_requires_review';
 END IF;
 UPDATE cron_dispatch_private.deployment SET probe_verified=true WHERE singleton;
 REVOKE EXECUTE ON FUNCTION public.cron_record_commit_probe(uuid),public.cron_check_commit_probe(uuid) FROM service_role;
 PERFORM cron.alter_job(a.job_id,active:=true);
 -- Manual prerequisites not inferred here: deployed Edge, patched workflow,
 -- matching trigger credentials, approved SHA, no GitHub run in progress,
 -- official dry-selection due=1, fresh READ ONLY baseline, operator watching.
END $arm$;
COMMIT;
