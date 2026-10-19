-- DRAFT. Does not activate a schedule. Metadata only; never pass a credential.
-- Parameters are session GUCs documented in ../README.md.
BEGIN;
DO $configure$
DECLARE
 project text := current_setting('app.cron_project_ref',true);
 permit uuid := nullif(current_setting('app.cron_authorization_id',true),'')::uuid;
 sha text := current_setting('app.cron_expected_sha',true);
 starts timestamptz := nullif(current_setting('app.cron_not_before',true),'')::timestamptz;
 expires timestamptz := nullif(current_setting('app.cron_expires_at',true),'')::timestamptz;
 selected_job bigint;
 existing cron_dispatch_private.authorizations%ROWTYPE;
BEGIN
 RAISE EXCEPTION 'inactive_preparation_review_blocked_see_review_md';
 IF current_setting('app.cron_sql_review',true) IS DISTINCT FROM 'staging-reviewed' OR current_user<>'postgres' THEN
   RAISE EXCEPTION 'draft_requires_staging_sql_review';
 END IF;
 IF project IS NULL OR project !~ '^[a-z0-9]{20}$' OR permit IS NULL
 OR sha IS NULL OR sha !~ '^[0-9a-f]{40}$' OR starts IS NULL OR expires IS NULL
 OR expires<=starts OR expires>starts+interval '5 minutes' THEN
   RAISE EXCEPTION 'reviewed_metadata_required';
 END IF;
 SELECT * INTO existing FROM cron_dispatch_private.authorizations WHERE authorization_id=permit;
 IF FOUND THEN
   IF existing.expected_sha<>sha OR existing.not_before<>starts OR existing.expires_at<>expires
   OR NOT EXISTS (SELECT 1 FROM cron_dispatch_private.deployment WHERE project_ref=project) THEN
     RAISE EXCEPTION 'existing_authorization_differs';
   END IF;
   -- Idempotent re-reading must never reset or reactivate a consumed permit.
   RETURN;
 END IF;
 IF EXISTS (SELECT 1 FROM cron.job WHERE jobname='cron-single-controlled-dispatch') THEN
   RAISE EXCEPTION 'existing_job_requires_review';
 END IF;
 INSERT INTO cron_dispatch_private.deployment(singleton,project_ref) VALUES(true,project)
 ON CONFLICT DO NOTHING;
 IF NOT EXISTS (SELECT 1 FROM cron_dispatch_private.deployment WHERE project_ref=project) THEN
   RAISE EXCEPTION 'staging_binding_differs';
 END IF;
 selected_job:=cron.schedule('cron-single-controlled-dispatch','* * * * *',
   format('SELECT cron_dispatch_private.enqueue_once(%L::uuid);',permit::text));
 PERFORM cron.alter_job(selected_job,active:=false);
 INSERT INTO cron_dispatch_private.authorizations
  (authorization_id,expected_sha,job_id,not_before,expires_at)
 VALUES(permit,sha,selected_job,starts,expires);
 -- No session can observe the newly created job active after this COMMIT.
END $configure$;
COMMIT;
