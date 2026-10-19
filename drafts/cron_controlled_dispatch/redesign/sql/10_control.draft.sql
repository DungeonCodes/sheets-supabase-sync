-- OFFLINE ONLY. Fresh v2 objects, not an upgrade of old drafts or the real probe.
BEGIN;
DO $review$
BEGIN
 RAISE EXCEPTION 'redesign_requires_human_deployment_review';
END $review$;
-- After future review, check role-name collisions and operator CREATEROLE first.
-- NO PASSWORD, LOGIN, token generation, or binding to authenticator here.
CREATE ROLE cron_dispatch_owner_v2 NOLOGIN NOSUPERUSER NOBYPASSRLS
 NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE cron_dispatch_edge_v2 NOLOGIN NOSUPERUSER NOBYPASSRLS
 NOCREATEDB NOCREATEROLE NOREPLICATION;
GRANT cron_dispatch_owner_v2 TO postgres;
CREATE SCHEMA cron_dispatch_v2 AUTHORIZATION cron_dispatch_owner_v2;
REVOKE ALL ON SCHEMA cron_dispatch_v2 FROM PUBLIC,anon,authenticated,service_role;
GRANT USAGE ON SCHEMA cron_dispatch_v2 TO cron_dispatch_edge_v2;
-- Schema must remain outside exposed API schemas. No public RPCs are created.
CREATE TABLE cron_dispatch_v2.permits (
 authorization_id uuid PRIMARY KEY,
 expected_sha text NOT NULL CHECK(expected_sha ~ '^[0-9a-f]{40}$'),
 ref text NOT NULL DEFAULT 'dev' CHECK(ref='dev'),
 job_id bigint NOT NULL UNIQUE,
 not_before timestamptz NOT NULL,
 expires_at timestamptz NOT NULL,
 state text NOT NULL DEFAULT 'armed' CHECK(state IN
  ('armed','released','consumed','accepted','ambiguous','http_error','expired','cancelled')),
 release_id uuid UNIQUE,
 released_at timestamptz,
 claim_count smallint NOT NULL DEFAULT 0 CHECK(claim_count IN (0,1)),
 claim_id uuid UNIQUE,
 consumed_at timestamptz,
 completed_at timestamptz,
 http_status integer CHECK(http_status BETWEEN 100 AND 599),
 github_run_id bigint UNIQUE CHECK(github_run_id>0),
 CHECK(expires_at>not_before AND expires_at<=not_before+interval '5 minutes'),
 CHECK((release_id IS NULL)=(released_at IS NULL)),
 CHECK(state NOT IN ('released','consumed','accepted','ambiguous','http_error') OR release_id IS NOT NULL),
 CHECK((claim_count=0 AND claim_id IS NULL AND consumed_at IS NULL)
    OR (claim_count=1 AND claim_id IS NOT NULL AND consumed_at IS NOT NULL)),
 CHECK((state IN ('consumed','accepted','ambiguous','http_error'))=(claim_count=1)),
 CHECK(state<>'accepted' OR (http_status=200 AND github_run_id IS NOT NULL)),
 CHECK(state='accepted' OR github_run_id IS NULL)
);
ALTER TABLE cron_dispatch_v2.permits OWNER TO cron_dispatch_owner_v2;
CREATE UNIQUE INDEX cron_dispatch_v2_one_live ON cron_dispatch_v2.permits((true))
 WHERE state IN ('armed','released','consumed');
REVOKE ALL ON ALL TABLES IN SCHEMA cron_dispatch_v2
 FROM PUBLIC,anon,authenticated,service_role,cron_dispatch_edge_v2;
-- No attempt to hide metadata from platform read-all/BYPASSRLS roles.
-- No PAT, connection string, bearer, signed capability, secret or raw HTTP body.
COMMIT;
