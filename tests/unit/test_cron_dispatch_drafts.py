from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
DRAFT = ROOT / "drafts" / "cron_controlled_dispatch"


def sql_without_comments(path: Path) -> str:
    return re.sub(r"--[^\n]*", "", path.read_text(encoding="utf-8")).lower()


class CronDraftSecurityContractTests(unittest.TestCase):
    """Offline artifact checks; do not imply SQL execution or PostgreSQL proof."""

    def test_write_scripts_require_explicit_review_and_have_no_destructive_cleanup(self) -> None:
        paths = sorted((DRAFT / "sql").glob("*.draft.sql"))
        self.assertEqual(6, len(paths))
        for path in paths:
            sql = sql_without_comments(path)
            with self.subTest(path=path.name):
                self.assertIn("current_setting('app.cron_", sql)
                self.assertIn("raise exception", sql)
                self.assertTrue(sql.strip().startswith("begin;"))
                self.assertNotRegex(sql, r"\b(delete\s+from|drop\s+(table|column|extension)|truncate)\b")
                self.assertNotIn("vault.create_secret", sql)

    def test_readonly_queries_never_dump_sensitive_catalog_columns(self) -> None:
        for name in ("00_inspect_readonly.sql", "60_validate_readonly.sql"):
            sql = sql_without_comments(DRAFT / "sql" / name)
            self.assertIn("begin read only;", sql)
            self.assertTrue(sql.strip().endswith("rollback;"))
            self.assertNotRegex(sql, r"select\s+\*")
            self.assertNotIn("decrypted_secret,", sql)
            self.assertNotIn("return_message", sql)
            self.assertNotIn("payload_json", sql)

    def test_github_pat_never_enters_sql_or_the_postgres_http_queue(self) -> None:
        sql = sql_without_comments(DRAFT / "sql" / "30_routines.draft.sql")
        self.assertIn("where name='cron_dispatch_edge_trigger'", sql)
        self.assertIn("trigger_credential !~ '^[0-9a-f]{64}$'", sql)
        self.assertNotIn("github_dispatch_pat", sql)
        self.assertNotIn("api.github.com", sql)
        self.assertEqual(1, sql.count("net.http_post("))
        edge = (DRAFT / "edge" / "index.ts").read_text(encoding="utf-8")
        self.assertIn('inactive_preparation_review_blocked', edge)
        self.assertNotIn('SUPABASE_SERVICE_ROLE_KEY', edge)
        redesigned = (DRAFT / "redesign" / "edge" / "dispatch.mjs").read_text(encoding="utf-8")
        self.assertIn('githubPat', redesigned)

    def test_definer_functions_fix_search_path_and_require_explicit_execute_grants(self) -> None:
        sql = sql_without_comments(DRAFT / "sql" / "30_routines.draft.sql")
        headers = re.findall(r"create or replace function\s+.*?\bas\s+\$\w+\$", sql, re.S)
        self.assertEqual(6, len(headers))
        for header in headers:
            self.assertIn("security definer set search_path=pg_catalog", header)
        self.assertIn("from public,anon,authenticated,service_role", sql)
        self.assertIn("to service_role", sql)
        self.assertNotIn("grant usage on schema cron_dispatch_private", sql)

    def test_legacy_claim_contains_xid_check_without_internal_commit(self) -> None:
        sql = sql_without_comments(DRAFT / "sql" / "30_routines.draft.sql")
        self.assertIn("claim_xid=pg_current_xact_id()", sql)
        self.assertIn("pg_xact_status(a.claim_xid)='committed'", sql)
        self.assertIn("set_config('synchronous_commit','on',true)", sql)
        self.assertIn("for update", sql)
        self.assertEqual(1, len(re.findall(r"\bcommit\s*;", sql)))  # outer DDL transaction only

    def test_legacy_acl_contains_revocations_not_proof_of_effective_access(self) -> None:
        sql = sql_without_comments(DRAFT / "sql" / "20_private_schema_and_acl.draft.sql")
        self.assertIn("revoke select on vault.secrets, vault.decrypted_secrets", sql)
        self.assertIn("revoke all on all tables in schema net", sql)
        self.assertIn("revoke usage on schema vault", sql)
        self.assertIn("has_table_privilege(role_name,'net.http_request_queue','select')", sql)
        self.assertIn("new.claim_count < old.claim_count", sql)
        self.assertIn("check (ref='dev')", sql)

    def test_job_is_created_inactive_and_activation_has_a_separate_gate(self) -> None:
        config = sql_without_comments(DRAFT / "sql" / "40_configure_inactive.draft.sql")
        arm = sql_without_comments(DRAFT / "sql" / "50_arm_once.draft.sql")
        rollback = sql_without_comments(DRAFT / "sql" / "70_disable_rollback.draft.sql")
        self.assertIn("cron.alter_job(selected_job,active:=false)", config)
        self.assertNotIn("active:=true", config)
        self.assertIn("one-cron-test-reviewed", arm)
        self.assertIn("public.cron_check_commit_probe(probe)", arm)
        self.assertIn("a.claim_count<>0", arm)
        self.assertIn("cron.alter_job(a.job_id,active:=false)", rollback)
        self.assertNotIn("claim_count=0", rollback.replace("a.claim_count=0", ""))

    def test_workflow_envelope_rejects_other_refs_and_reruns_without_touching_real_workflow(self) -> None:
        fragment = (DRAFT / "workflow-envelope.fragment.yml").read_text(encoding="utf-8")
        self.assertIn('test "$GITHUB_REF" = refs/heads/dev', fragment)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1', fragment)
        self.assertIn('test "$GITHUB_SHA" = "$EXPECTED_SHA"', fragment)
        self.assertNotIn("secrets.", fragment)


if __name__ == "__main__":
    unittest.main()
