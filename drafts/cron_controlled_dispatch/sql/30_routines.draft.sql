-- DRAFT: ordinary transactions, never an assumed COMMIT inside a function.
BEGIN;
DO $review$
BEGIN
 RAISE EXCEPTION 'inactive_preparation_review_blocked_see_review_md';
 IF current_setting('app.cron_sql_review', true) IS DISTINCT FROM 'staging-reviewed' OR current_user <> 'postgres' THEN
   RAISE EXCEPTION 'draft_requires_staging_sql_review';
 END IF;
END $review$;

CREATE OR REPLACE FUNCTION cron_dispatch_private.enqueue_once(p_authorization uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $enqueue$
DECLARE
 a cron_dispatch_private.authorizations%ROWTYPE;
 project text;
 trigger_credential text;
 request_id bigint;
BEGIN
 SELECT * INTO a FROM cron_dispatch_private.authorizations
  WHERE authorization_id=p_authorization FOR UPDATE;
 IF NOT FOUND THEN RETURN; END IF;
 IF a.outcome <> 'armed' OR a.enqueue_count <> 0 THEN
   PERFORM cron.alter_job(a.job_id, active:=false);
   RETURN;
 END IF;
 IF clock_timestamp() < a.not_before THEN RETURN; END IF;
 IF clock_timestamp() >= a.expires_at THEN
   UPDATE cron_dispatch_private.authorizations SET outcome='expired' WHERE authorization_id=p_authorization;
   PERFORM cron.alter_job(a.job_id, active:=false);
   RETURN;
 END IF;
 IF a.ref <> 'dev' OR NOT EXISTS (SELECT 1 FROM cron_dispatch_private.deployment WHERE probe_verified) THEN
   RAISE EXCEPTION 'dispatch_not_ready';
 END IF;
 IF NOT EXISTS (SELECT 1 FROM cron.job WHERE jobid=a.job_id AND username='postgres'
   AND database=current_database() AND jobname='cron-single-controlled-dispatch'
   AND command=format('SELECT cron_dispatch_private.enqueue_once(%L::uuid);',p_authorization::text)) THEN
   RAISE EXCEPTION 'cron_binding_invalid';
 END IF;
 SELECT project_ref INTO STRICT project FROM cron_dispatch_private.deployment;
 -- Dedicated Edge trigger credential only. Never a GitHub PAT or service key.
 BEGIN
   SELECT decrypted_secret INTO STRICT trigger_credential FROM vault.decrypted_secrets
    WHERE name='cron_dispatch_edge_trigger';
   IF trigger_credential IS NULL OR trigger_credential !~ '^[0-9a-f]{64}$' THEN
     RAISE EXCEPTION 'trigger_configuration_invalid';
   END IF;
   PERFORM cron.alter_job(a.job_id, active:=false);
   request_id := net.http_post(
     url:=format('https://%s.supabase.co/functions/v1/cron-controlled-dispatch',project),
     body:=jsonb_build_object('authorization_id',p_authorization),
     headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||trigger_credential),
     timeout_milliseconds:=45000);
 EXCEPTION WHEN OTHERS THEN
   -- Do not propagate an extension error containing evaluated headers/row data.
   RAISE EXCEPTION 'enqueue_failed_sensitive_details_suppressed' USING ERRCODE='P0001';
 END;
 trigger_credential := NULL;
 UPDATE cron_dispatch_private.authorizations SET enqueue_count=1,outcome='queued',
   net_request_id=request_id,cron_backend_pid=pg_backend_pid(),enqueued_at=clock_timestamp()
  WHERE authorization_id=p_authorization;
 -- Queue and state become visible together at the outer Cron transaction commit.
 -- Worker delivery may repeat; Edge claim below is the irreversible send barrier.
END $enqueue$;

CREATE OR REPLACE FUNCTION public.cron_claim_dispatch(p_authorization uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $claim$
DECLARE a cron_dispatch_private.authorizations%ROWTYPE; receipt uuid;
BEGIN
 PERFORM set_config('synchronous_commit','on',true);
 SELECT * INTO a FROM cron_dispatch_private.authorizations
  WHERE authorization_id=p_authorization FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('claimed',false); END IF;
 IF a.outcome<>'queued' OR a.enqueue_count<>1 OR a.claim_count<>0 OR a.ref<>'dev'
 OR clock_timestamp()<a.not_before OR clock_timestamp()>=a.expires_at THEN
   IF a.claim_count=0 AND clock_timestamp()>=a.expires_at AND a.outcome IN ('armed','queued') THEN
     UPDATE cron_dispatch_private.authorizations SET outcome='expired' WHERE authorization_id=p_authorization;
   END IF;
   RETURN jsonb_build_object('claimed',false);
 END IF;
 IF NOT EXISTS (SELECT 1 FROM cron_dispatch_private.deployment WHERE probe_verified)
 OR NOT EXISTS (SELECT 1 FROM cron.job WHERE jobid=a.job_id AND NOT active) THEN
   RETURN jsonb_build_object('claimed',false);
 END IF;
 receipt:=gen_random_uuid();
 UPDATE cron_dispatch_private.authorizations SET claim_count=1,outcome='consumed',
   claim_id=receipt,claim_xid=pg_current_xact_id(),consumed_at=clock_timestamp()
  WHERE authorization_id=p_authorization;
 RETURN jsonb_build_object('claimed',true,'authorization_id',p_authorization,
   'claim_id',receipt,'ref',a.ref,'expected_sha',a.expected_sha,'expires_at',a.expires_at);
 -- No HTTP here. PostgREST ends and commits this transaction before returning.
END $claim$;

CREATE OR REPLACE FUNCTION public.cron_confirm_dispatch_claim(p_authorization uuid,p_claim uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $confirm$
DECLARE a cron_dispatch_private.authorizations%ROWTYPE;
BEGIN
 SELECT * INTO a FROM cron_dispatch_private.authorizations WHERE authorization_id=p_authorization;
 IF NOT FOUND THEN RETURN false; END IF;
 RETURN a.claim_count=1 AND a.claim_id=p_claim AND a.outcome='consumed'
   AND a.ref='dev' AND clock_timestamp()<a.expires_at
   AND pg_xact_status(a.claim_xid)='committed'
   AND EXISTS (SELECT 1 FROM cron.job WHERE jobid=a.job_id AND NOT active);
 -- A second RPC transaction must observe committed consumption, not command order.
END $confirm$;

CREATE OR REPLACE FUNCTION public.cron_finish_dispatch(
 p_authorization uuid,p_claim uuid,p_outcome text,p_http_status integer,p_run_id bigint)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $finish$
BEGIN
 IF p_outcome NOT IN ('accepted','http_error','ambiguous') OR p_outcome IS NULL
 OR (p_http_status IS NOT NULL AND p_http_status NOT BETWEEN 100 AND 599)
 OR (p_outcome='accepted' AND (p_http_status IS DISTINCT FROM 200 OR p_run_id IS NULL OR p_run_id<=0))
 OR (p_outcome<>'accepted' AND p_run_id IS NOT NULL) THEN
   RETURN false;
 END IF;
 UPDATE cron_dispatch_private.authorizations SET outcome=p_outcome,http_status=p_http_status,
   github_run_id=p_run_id,completed_at=clock_timestamp()
  WHERE authorization_id=p_authorization AND claim_id=p_claim AND claim_count=1 AND outcome='consumed';
 RETURN FOUND;
END $finish$;

-- No-GitHub deployment probe. Two separate RPC requests are mandatory.
CREATE OR REPLACE FUNCTION public.cron_record_commit_probe(p_probe uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $probe$
BEGIN
 IF EXISTS (SELECT 1 FROM cron_dispatch_private.deployment WHERE probe_verified) THEN RETURN false; END IF;
 PERFORM set_config('synchronous_commit','on',true);
 INSERT INTO cron_dispatch_private.commit_probes(probe_id,transaction_id)
  VALUES(p_probe,pg_current_xact_id()) ON CONFLICT DO NOTHING;
 RETURN FOUND;
END $probe$;
CREATE OR REPLACE FUNCTION public.cron_check_commit_probe(p_probe uuid)
RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $probe_check$
 SELECT coalesce((SELECT pg_xact_status(transaction_id)='committed'
   FROM cron_dispatch_private.commit_probes WHERE probe_id=p_probe),false);
$probe_check$;

ALTER FUNCTION cron_dispatch_private.enqueue_once(uuid) OWNER TO postgres;
ALTER FUNCTION public.cron_claim_dispatch(uuid) OWNER TO postgres;
ALTER FUNCTION public.cron_confirm_dispatch_claim(uuid,uuid) OWNER TO postgres;
ALTER FUNCTION public.cron_finish_dispatch(uuid,uuid,text,integer,bigint) OWNER TO postgres;
ALTER FUNCTION public.cron_record_commit_probe(uuid) OWNER TO postgres;
ALTER FUNCTION public.cron_check_commit_probe(uuid) OWNER TO postgres;

REVOKE ALL ON FUNCTION cron_dispatch_private.enqueue_once(uuid) FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.cron_claim_dispatch(uuid),
 public.cron_confirm_dispatch_claim(uuid,uuid),public.cron_finish_dispatch(uuid,uuid,text,integer,bigint),
 public.cron_record_commit_probe(uuid),public.cron_check_commit_probe(uuid)
 FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.cron_claim_dispatch(uuid),
 public.cron_confirm_dispatch_claim(uuid,uuid),public.cron_finish_dispatch(uuid,uuid,text,integer,bigint),
 public.cron_record_commit_probe(uuid),public.cron_check_commit_probe(uuid) TO service_role;
COMMIT;
