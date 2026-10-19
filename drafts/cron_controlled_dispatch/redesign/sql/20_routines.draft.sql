-- OFFLINE ONLY. Three Edge capabilities; release/cancel remain operator-only.
BEGIN;
DO $review$
BEGIN
 RAISE EXCEPTION 'redesign_requires_human_deployment_review';
END $review$;
CREATE FUNCTION cron_dispatch_v2.no_rearm() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $guard$
BEGIN
 IF (NEW.authorization_id,NEW.expected_sha,NEW.ref,NEW.job_id,NEW.not_before,NEW.expires_at)
   IS DISTINCT FROM (OLD.authorization_id,OLD.expected_sha,OLD.ref,OLD.job_id,OLD.not_before,OLD.expires_at)
 OR NEW.claim_count<OLD.claim_count
 OR (OLD.release_id IS NOT NULL AND (NEW.release_id,NEW.released_at)
   IS DISTINCT FROM (OLD.release_id,OLD.released_at))
 OR (OLD.claim_count=1 AND (NEW.claim_id,NEW.consumed_at)
   IS DISTINCT FROM (OLD.claim_id,OLD.consumed_at))
 OR NOT (
   (OLD.state='armed' AND NEW.state IN ('released','expired','cancelled')) OR
   (OLD.state='released' AND NEW.state IN ('consumed','expired','cancelled')) OR
   (OLD.state='consumed' AND NEW.state IN ('accepted','ambiguous','http_error'))
 ) THEN RAISE EXCEPTION 'permit_cannot_be_rearmed'; END IF;
 RETURN NEW;
END $guard$;
CREATE TRIGGER no_rearm BEFORE UPDATE ON cron_dispatch_v2.permits
 FOR EACH ROW EXECUTE FUNCTION cron_dispatch_v2.no_rearm();

-- Called only by the reviewed Cron wrapper/operator, never granted to Edge.
-- Job provenance must be validated in that wrapper before this invocation.
CREATE FUNCTION cron_dispatch_v2.release(p_id uuid,p_job bigint) RETURNS boolean
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $release$
DECLARE a cron_dispatch_v2.permits%ROWTYPE;
BEGIN
 SELECT * INTO a FROM cron_dispatch_v2.permits WHERE authorization_id=p_id FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 IF a.state<>'armed' OR a.job_id<>p_job OR a.ref<>'dev'
 OR clock_timestamp()<a.not_before OR clock_timestamp()>=a.expires_at THEN RETURN false; END IF;
 UPDATE cron_dispatch_v2.permits SET state='released',release_id=gen_random_uuid(),
  released_at=clock_timestamp() WHERE authorization_id=p_id;
 RETURN true;
END $release$;

CREATE FUNCTION cron_dispatch_v2.claim(p_id uuid,p_sha text,p_release uuid) RETURNS jsonb
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $claim$
DECLARE a cron_dispatch_v2.permits%ROWTYPE; receipt uuid;
BEGIN
 PERFORM set_config('synchronous_commit','on',true);
 SELECT * INTO a FROM cron_dispatch_v2.permits WHERE authorization_id=p_id FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('claimed',false); END IF;
 IF a.state<>'released' OR a.claim_count<>0 OR a.ref<>'dev'
 OR a.expected_sha IS DISTINCT FROM p_sha OR a.release_id IS DISTINCT FROM p_release
 OR p_release IS NULL OR clock_timestamp()<a.not_before OR clock_timestamp()>=a.expires_at THEN
  RETURN jsonb_build_object('claimed',false);
 END IF;
 receipt:=gen_random_uuid();
 UPDATE cron_dispatch_v2.permits SET state='consumed',claim_count=1,
  claim_id=receipt,consumed_at=clock_timestamp() WHERE authorization_id=p_id;
 RETURN jsonb_build_object('claimed',true,'authorization_id',p_id,'claim_id',receipt,
  'release_id',a.release_id,'repository','DungeonCodes/sheets-supabase-sync',
  'workflow','scheduled-sync.yml','ref',a.ref,'expected_sha',a.expected_sha,'expires_at',a.expires_at);
END $claim$;

CREATE FUNCTION cron_dispatch_v2.confirm(p_id uuid,p_receipt uuid) RETURNS boolean
 LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $confirm$
 SELECT EXISTS(SELECT 1 FROM cron_dispatch_v2.permits WHERE authorization_id=p_id
  AND claim_id=p_receipt AND claim_count=1 AND state='consumed' AND ref='dev'
  AND clock_timestamp()>=not_before AND clock_timestamp()<expires_at);
$confirm$;

CREATE FUNCTION cron_dispatch_v2.finish(p_id uuid,p_receipt uuid,p_outcome text,p_http integer,p_run bigint)
 RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $finish$
BEGIN
 IF p_outcome IS NULL OR p_outcome NOT IN ('accepted','ambiguous','http_error')
 OR (p_http IS NOT NULL AND p_http NOT BETWEEN 100 AND 599)
 OR (p_outcome='accepted' AND (p_http IS DISTINCT FROM 200 OR p_run IS NULL OR p_run<=0))
 OR (p_outcome<>'accepted' AND p_run IS NOT NULL) THEN RETURN false; END IF;
 UPDATE cron_dispatch_v2.permits SET state=p_outcome,http_status=p_http,
  github_run_id=p_run,completed_at=clock_timestamp()
  WHERE authorization_id=p_id AND claim_id=p_receipt AND claim_count=1 AND state='consumed';
 RETURN FOUND;
END $finish$;

CREATE FUNCTION cron_dispatch_v2.cancel(p_id uuid) RETURNS boolean
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $cancel$
BEGIN
 UPDATE cron_dispatch_v2.permits SET state='cancelled',completed_at=clock_timestamp()
  WHERE authorization_id=p_id AND state IN ('armed','released') AND claim_count=0;
 RETURN FOUND;
END $cancel$;

ALTER FUNCTION cron_dispatch_v2.no_rearm() OWNER TO cron_dispatch_owner_v2;
ALTER FUNCTION cron_dispatch_v2.release(uuid,bigint) OWNER TO cron_dispatch_owner_v2;
ALTER FUNCTION cron_dispatch_v2.claim(uuid,text,uuid) OWNER TO cron_dispatch_owner_v2;
ALTER FUNCTION cron_dispatch_v2.confirm(uuid,uuid) OWNER TO cron_dispatch_owner_v2;
ALTER FUNCTION cron_dispatch_v2.finish(uuid,uuid,text,integer,bigint) OWNER TO cron_dispatch_owner_v2;
ALTER FUNCTION cron_dispatch_v2.cancel(uuid) OWNER TO cron_dispatch_owner_v2;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA cron_dispatch_v2
 FROM PUBLIC,anon,authenticated,service_role,cron_dispatch_edge_v2;
GRANT EXECUTE ON FUNCTION cron_dispatch_v2.claim(uuid,text,uuid),
 cron_dispatch_v2.confirm(uuid,uuid),cron_dispatch_v2.finish(uuid,uuid,text,integer,bigint)
 TO cron_dispatch_edge_v2;
GRANT EXECUTE ON FUNCTION cron_dispatch_v2.release(uuid,bigint),cron_dispatch_v2.cancel(uuid) TO postgres;
COMMIT;
