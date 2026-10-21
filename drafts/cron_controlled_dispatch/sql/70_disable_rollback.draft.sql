-- DRAFT. Stop future sends, preserve evidence; never undo a consumed claim.
BEGIN;
DO $disable$
DECLARE
 permit uuid := nullif(current_setting('app.cron_authorization_id',true),'')::uuid;
 a cron_dispatch_private.authorizations%ROWTYPE;
BEGIN
 IF current_setting('app.cron_sql_review',true) IS DISTINCT FROM 'staging-reviewed'
 OR current_user<>'postgres' THEN RAISE EXCEPTION 'draft_requires_staging_sql_review'; END IF;
 IF permit IS NULL THEN RAISE EXCEPTION 'authorization_id_required'; END IF;
 SELECT * INTO a FROM cron_dispatch_private.authorizations WHERE authorization_id=permit FOR UPDATE;
 IF NOT FOUND THEN RETURN; END IF;
 PERFORM cron.alter_job(a.job_id,active:=false);
 IF a.claim_count=0 AND a.outcome IN ('armed','queued') THEN
   UPDATE cron_dispatch_private.authorizations SET outcome='cancelled',completed_at=clock_timestamp()
    WHERE authorization_id=permit;
 END IF;
 -- A request already queued can still reach Edge; cancelled/consumed state
 -- prevents another GitHub send. An accepted GitHub dispatch cannot be undone.
END $disable$;
COMMIT;
-- Human follow-up: confirm active=false, reconcile existing run, revoke a PAT
-- dedicated to this test and disable the Edge route. No destructive cleanup.
