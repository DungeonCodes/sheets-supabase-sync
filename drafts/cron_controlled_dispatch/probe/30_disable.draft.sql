-- Logical rollback only: preserve the tiny isolated evidence, never reset claims.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='10s';
DO $review$
BEGIN
 IF current_user <> 'postgres' OR current_setting('app.cron_probe_review',true)
    IS DISTINCT FROM 'isolated-staging-reviewed' THEN
   RAISE EXCEPTION 'isolated_probe_approval_required';
 END IF;
END $review$;
UPDATE cron_tx_probe.control SET enabled=false WHERE singleton;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA cron_tx_probe FROM PUBLIC,anon,authenticated,service_role;
COMMIT;
BEGIN READ ONLY;
SELECT NOT enabled AS disabled FROM cron_tx_probe.control WHERE singleton;
ROLLBACK;
