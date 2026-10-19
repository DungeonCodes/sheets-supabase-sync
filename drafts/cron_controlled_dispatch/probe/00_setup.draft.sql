-- REVIEW DRAFT ONLY. Fresh isolated objects; no extensions or external calls.
-- Run only after the staging guard and separate human approval, with ON_ERROR_STOP.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='10s';
DO $review$
BEGIN
 IF current_user <> 'postgres' OR current_setting('app.cron_probe_review',true)
    IS DISTINCT FROM 'isolated-staging-reviewed' THEN
   RAISE EXCEPTION 'isolated_probe_approval_required';
 END IF;
 IF to_regnamespace('cron_tx_probe') IS NOT NULL THEN
   RAISE EXCEPTION 'probe_schema_exists_do_not_reset';
 END IF;
END $review$;
CREATE SCHEMA cron_tx_probe AUTHORIZATION postgres;
REVOKE ALL ON SCHEMA cron_tx_probe FROM PUBLIC,anon,authenticated,service_role;
CREATE TABLE cron_tx_probe.control (
 singleton boolean PRIMARY KEY CHECK(singleton),
 enabled boolean NOT NULL,
 expires_at timestamptz NOT NULL
);
CREATE TABLE cron_tx_probe.permits (
 case_name text PRIMARY KEY CHECK(case_name IN ('rollback','race','expired')),
 ref text NOT NULL DEFAULT 'dev' CHECK(ref='dev'),
 expires_at timestamptz NOT NULL,
 claim_count integer NOT NULL DEFAULT 0 CHECK(claim_count IN (0,1)),
 claimant_pid integer,
 CHECK((claim_count=0 AND claimant_pid IS NULL) OR
       (claim_count=1 AND claimant_pid IS NOT NULL))
);
CREATE FUNCTION cron_tx_probe.no_rearm() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $guard$
BEGIN
 IF (NEW.case_name,NEW.ref,NEW.expires_at) IS DISTINCT FROM
    (OLD.case_name,OLD.ref,OLD.expires_at)
 OR NEW.claim_count < OLD.claim_count
 OR (OLD.claim_count=1 AND NEW.claimant_pid IS DISTINCT FROM OLD.claimant_pid) THEN
   RAISE EXCEPTION 'probe_permit_immutable';
 END IF;
 RETURN NEW;
END $guard$;
CREATE TRIGGER no_rearm BEFORE UPDATE ON cron_tx_probe.permits
 FOR EACH ROW EXECUTE FUNCTION cron_tx_probe.no_rearm();
CREATE FUNCTION cron_tx_probe.claim(p_case text) RETURNS boolean
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $claim$
DECLARE candidate cron_tx_probe.permits%ROWTYPE;
BEGIN
 IF current_user <> 'postgres' OR current_setting('app.cron_probe_review',true)
    IS DISTINCT FROM 'isolated-staging-reviewed' THEN
   RAISE EXCEPTION 'isolated_probe_approval_required';
 END IF;
 PERFORM set_config('synchronous_commit','on',true);
 -- Shared control lock serializes cancellation with a claim, not with other claims.
 PERFORM 1 FROM cron_tx_probe.control WHERE singleton AND enabled
   AND expires_at>clock_timestamp() FOR SHARE;
 IF NOT FOUND THEN RETURN false; END IF;
 SELECT * INTO candidate FROM cron_tx_probe.permits WHERE case_name=p_case FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 -- Recheck time AFTER obtaining locks, including a potentially blocked row lock.
 IF candidate.claim_count<>0 OR candidate.ref<>'dev'
 OR candidate.expires_at<=clock_timestamp()
 OR NOT EXISTS(SELECT 1 FROM cron_tx_probe.control WHERE singleton AND enabled
               AND expires_at>clock_timestamp()) THEN RETURN false; END IF;
 UPDATE cron_tx_probe.permits SET claim_count=1,claimant_pid=pg_backend_pid()
  WHERE case_name=p_case;
 RETURN true;
END $claim$;
REVOKE ALL ON ALL TABLES IN SCHEMA cron_tx_probe FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA cron_tx_probe FROM PUBLIC,anon,authenticated,service_role;
INSERT INTO cron_tx_probe.control VALUES(true,true,clock_timestamp()+interval '30 minutes');
INSERT INTO cron_tx_probe.permits(case_name,expires_at) VALUES
 ('rollback',clock_timestamp()+interval '30 minutes'),
 ('race',clock_timestamp()+interval '30 minutes'),
 ('expired',clock_timestamp()-interval '1 second');
COMMIT;
