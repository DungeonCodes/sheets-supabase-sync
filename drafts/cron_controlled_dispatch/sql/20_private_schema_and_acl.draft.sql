-- DRAFT. No secret values; review existing dependencies before revoking grants.
BEGIN;
DO $review$
BEGIN
 RAISE EXCEPTION 'inactive_preparation_review_blocked_see_review_md';
 IF current_setting('app.cron_sql_review', true) IS DISTINCT FROM 'staging-reviewed' OR current_user <> 'postgres' THEN
   RAISE EXCEPTION 'draft_requires_staging_sql_review';
 END IF;
END $review$;
CREATE SCHEMA IF NOT EXISTS cron_dispatch_private AUTHORIZATION postgres;
DO $owner$
BEGIN
 IF EXISTS (SELECT 1 FROM pg_namespace n JOIN pg_roles r ON r.oid=n.nspowner
   WHERE n.nspname='cron_dispatch_private' AND r.rolname<>'postgres') THEN
   RAISE EXCEPTION 'private_schema_owner_requires_review';
 END IF;
END $owner$;
REVOKE ALL ON SCHEMA cron_dispatch_private FROM PUBLIC, anon, authenticated, service_role;
REVOKE USAGE ON SCHEMA vault FROM PUBLIC, anon, authenticated, service_role;
REVOKE SELECT ON vault.secrets, vault.decrypted_secrets FROM PUBLIC, anon, authenticated, service_role;
-- pg_net defaults are broad. A dedicated trigger credential must not be readable
-- by client roles, even though the GitHub PAT will never enter this queue.
REVOKE USAGE ON SCHEMA net FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON ALL TABLES IN SCHEMA net FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA net FROM PUBLIC, anon, authenticated, service_role;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA net FROM PUBLIC, anon, authenticated, service_role;

CREATE TABLE IF NOT EXISTS cron_dispatch_private.deployment (
 singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
 schema_version integer NOT NULL DEFAULT 1 CHECK (schema_version=1),
 project_ref text NOT NULL CHECK (project_ref ~ '^[a-z0-9]{20}$'),
 probe_verified boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS cron_dispatch_private.authorizations (
 authorization_id uuid PRIMARY KEY,
 ref text NOT NULL DEFAULT 'dev' CHECK (ref='dev'),
 expected_sha text NOT NULL CHECK (expected_sha ~ '^[0-9a-f]{40}$'),
 job_id bigint NOT NULL UNIQUE,
 not_before timestamptz NOT NULL,
 expires_at timestamptz NOT NULL,
 enqueue_count smallint NOT NULL DEFAULT 0 CHECK (enqueue_count IN (0,1)),
 claim_count smallint NOT NULL DEFAULT 0 CHECK (claim_count IN (0,1)),
 outcome text NOT NULL DEFAULT 'armed' CHECK (outcome IN
   ('armed','queued','consumed','accepted','http_error','ambiguous','expired','cancelled','configuration_error')),
 net_request_id bigint UNIQUE,
 cron_backend_pid integer,
 enqueued_at timestamptz,
 claim_id uuid UNIQUE,
 claim_xid xid8,
 consumed_at timestamptz,
 completed_at timestamptz,
 http_status integer CHECK (http_status BETWEEN 100 AND 599),
 github_run_id bigint UNIQUE CHECK (github_run_id > 0),
 CHECK (expires_at > not_before AND expires_at <= not_before + interval '5 minutes'),
 CHECK (claim_count <= enqueue_count),
 CHECK ((claim_count=0 AND claim_id IS NULL AND claim_xid IS NULL AND consumed_at IS NULL)
     OR (claim_count=1 AND claim_id IS NOT NULL AND claim_xid IS NOT NULL AND consumed_at IS NOT NULL)),
 CHECK (outcome <> 'accepted' OR (github_run_id IS NOT NULL AND http_status=200))
);
CREATE UNIQUE INDEX IF NOT EXISTS cron_dispatch_one_live_authorization
 ON cron_dispatch_private.authorizations ((true)) WHERE outcome IN ('armed','queued','consumed');
CREATE TABLE IF NOT EXISTS cron_dispatch_private.commit_probes (
 probe_id uuid PRIMARY KEY,
 transaction_id xid8 NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE OR REPLACE FUNCTION cron_dispatch_private.guard_authorization()
RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $guard$
BEGIN
 IF (NEW.authorization_id,NEW.ref,NEW.expected_sha,NEW.job_id,NEW.not_before,NEW.expires_at)
     IS DISTINCT FROM (OLD.authorization_id,OLD.ref,OLD.expected_sha,OLD.job_id,OLD.not_before,OLD.expires_at)
 OR NEW.enqueue_count < OLD.enqueue_count OR NEW.claim_count < OLD.claim_count
 OR (OLD.claim_count=1 AND (NEW.claim_id,NEW.claim_xid,NEW.consumed_at)
     IS DISTINCT FROM (OLD.claim_id,OLD.claim_xid,OLD.consumed_at))
 OR (OLD.enqueue_count=1 AND NEW.outcome='armed')
 OR (OLD.claim_count=1 AND NEW.outcome IN ('armed','queued')) THEN
   RAISE EXCEPTION 'authorization_cannot_be_rearmed';
 END IF;
 RETURN NEW;
END $guard$;
CREATE OR REPLACE TRIGGER cron_dispatch_authorization_immutable
 BEFORE UPDATE ON cron_dispatch_private.authorizations FOR EACH ROW
 EXECUTE FUNCTION cron_dispatch_private.guard_authorization();
REVOKE ALL ON ALL TABLES IN SCHEMA cron_dispatch_private FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA cron_dispatch_private FROM PUBLIC, anon, authenticated, service_role;
DO $acl$
DECLARE role_name text;
BEGIN
 FOREACH role_name IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
   IF has_schema_privilege(role_name,'vault','USAGE')
   OR has_table_privilege(role_name,'vault.decrypted_secrets','SELECT')
   OR has_any_column_privilege(role_name,'vault.decrypted_secrets','SELECT')
   OR has_table_privilege(role_name,'net.http_request_queue','SELECT')
   OR has_any_column_privilege(role_name,'net.http_request_queue','SELECT')
   OR has_schema_privilege(role_name,'cron_dispatch_private','USAGE') THEN
     RAISE EXCEPTION 'effective_privileges_require_review';
   END IF;
 END LOOP;
END $acl$;
DO $table_owners$
BEGIN
 IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   JOIN pg_roles r ON r.oid=c.relowner WHERE n.nspname='cron_dispatch_private'
   AND c.relkind IN ('r','p') AND r.rolname<>'postgres') THEN
   RAISE EXCEPTION 'private_table_owner_requires_review';
 END IF;
END $table_owners$;
COMMIT;
