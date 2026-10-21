"""Offline behavioral regression of isolated CLI patch and exact workflow adapter."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from datetime import UTC, datetime
from sheets_supabase_sync.sources import DataSource, InstitutionConfig
from sheets_supabase_sync.dispatcher import OperationalSource
from sheets_supabase_sync.errors import SyncError, ErrorCode

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sheets_supabase_sync.batch_cli_candidate", ROOT / "batch_cli.candidate.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
NOW = datetime(2026, 10, 21, tzinfo=UTC)

def run_candidate(kinds, *, due=True, infrastructure=False, dry=False):
    sources = tuple(DataSource(f"fixture{i}", f"synthetic-sheet{i}", "Fixture", f"fixture{i}_raw", ("id",), 60) for i in range(len(kinds)))
    states = {s.name: OperationalSource(s.name, s.spreadsheet_id, s.sheet_name, s.target_table, s.business_key, True, "active", None if due else NOW) for s in sources}
    executed, outputs = [], []
    def operation(_root, _env, source, _mode):
        index = sources.index(source)
        executed.append(index)
        if kinds[index] == "failed":
            raise SyncError(ErrorCode.DATABASE, "synthetic-private-failure")
        if kinds[index] == "busy":
            raise SyncError(ErrorCode.BUSY, "synthetic-private-busy")
        return SimpleNamespace(plan=SimpleNamespace(counts={"new": 0 if kinds[index] == "no_changes" else 1, "changed": 0, "removed": 0, "restored": 0}), persisted=True)
    def load_states(*_):
        if infrastructure:
            raise SyncError(ErrorCode.DATABASE, "synthetic-private-infrastructure")
        return states
    with patch.object(cli, "validate_staging_access"):
        code = cli.run_cli(["--config", "synthetic.json", "--dry-select" if dry else "--confirm-staging"],
            environment_loader=lambda _: SimpleNamespace(db_url="postgresql://fixture@localhost/fixture"),
            institution_loader=lambda _: InstitutionConfig("fixture", "isolated", sources),
            state_loader=load_states, operation=operation, now=lambda: NOW, emit=outputs.append)
    return code, json.loads(outputs[-1]), executed

class CliRegression(unittest.TestCase):
    def test_partial_failure_preserves_following_success_and_evidence(self):
        code, summary, executed = run_candidate(["failed", "success"])
        self.assertEqual(1, code)
        self.assertEqual([0, 1], executed)
        self.assertEqual(1, summary["sources_failed"])
        self.assertEqual(2, summary["sources_executed"])
        self.assertEqual(["failed", "applied"], [x["status"] for x in summary["sources"]])
    def test_no_changes_success(self):
        code, summary, _ = run_candidate(["no_changes"])
        self.assertEqual((0, 1, 0), (code, summary["sources_no_changes"], summary["sources_failed"]))
    def test_busy_deferred_not_failure(self):
        code, summary, _ = run_candidate(["busy"])
        self.assertEqual((0, 1, 0), (code, summary["sources_busy_deferred"], summary["sources_failed"]))
    def test_no_due_does_not_execute(self):
        code, summary, executed = run_candidate(["success"], due=False)
        self.assertEqual((0, 0, []), (code, summary["sources_due"], executed))
    def test_infrastructure_has_distinct_exit(self):
        code, summary, executed = run_candidate(["success"], infrastructure=True)
        self.assertEqual((2, "failed", []), (code, summary["status"], executed))
        self.assertNotIn("synthetic-private", json.dumps(summary))
    def test_dry_selection_does_not_execute(self):
        code, summary, executed = run_candidate(["success"], dry=True)
        self.assertEqual((0, "selected", []), (code, summary["status"], executed))
    def test_patch_is_only_exit_code_change(self):
        original = (ROOT.parent.parent / "src/sheets_supabase_sync/batch_cli.py").read_text(encoding="utf-8")
        self.assertEqual(original.replace("    return 0\n", "    return 1 if summary.sources_failed else 0\n"), (ROOT/"batch_cli.candidate.py").read_text(encoding="utf-8"))

class PublicSummaryAdapter(unittest.TestCase):
    def execute_adapter(self, summary, code):
        workflow=(ROOT/"scheduled-sync.candidate.yml").read_text(encoding="utf-8")
        block=workflow.split("# EXECUTOR_SUMMARY_BEGIN\n")[1].split("# EXECUTOR_SUMMARY_END")[0]
        block="\n".join(line[10:] if line.startswith("          ") else line for line in block.splitlines())
        from sheets_supabase_sync import batch_cli
        def fake_cli(_args, *, emit):
            emit(json.dumps(summary))
            return code
        printed=[]
        with patch.object(batch_cli,"run_cli",fake_cli), patch("builtins.print",side_effect=printed.append):
            with self.assertRaises(SystemExit) as result:
                exec(compile(block,"workflow-adapter","exec"),{})
        return result.exception.code, json.loads(printed[-1])
    def summary(self, **changes):
        return dict(sources_total=1,sources_due=1,sources_executed=1,sources_failed=0,sources_busy_deferred=0,sources_no_changes=0,sources_skipped=0,**changes)
    def test_legacy_zero_exit_partial_failure_is_caught(self):
        summary=self.summary(); summary["sources_failed"]=1
        code, public=self.execute_adapter(summary,0)
        self.assertEqual((1,"EXECUTOR_PARTIAL_FAILURE"),(code,public["state"]))
    def test_private_source_fields_removed(self):
        summary=self.summary(); summary["sources"]=[{"source":"synthetic-private"}]; summary["password"]="synthetic-private"
        code, public=self.execute_adapter(summary,0)
        self.assertEqual(0,code); self.assertNotIn("synthetic-private",json.dumps(public))
    def test_infrastructure_failure(self):
        code, result = self.execute_adapter({"status":"failed"},2)
        self.assertEqual((2,"EXECUTOR_FAILED","SUMMARY_UNAVAILABLE"),(code,result["state"],result["code"]))
    def test_unknown_evidence_not_reported_as_proven_failure(self):
        code, result = self.execute_adapter({},0)
        self.assertEqual((2,"EXECUTOR_UNKNOWN","SUMMARY_UNAVAILABLE"),(code,result["state"],result["code"]))
    def test_no_changes_and_busy_and_no_due(self):
        for field, value, state in [("sources_no_changes",1,"EXECUTOR_SUCCESS"),("sources_busy_deferred",1,"CLOCK_BUSY"),("sources_due",0,"CLOCK_SKIPPED_NO_DUE")]:
            summary=self.summary(); summary[field]=value
            self.assertEqual((0,state), (lambda r:(r[0],r[1]["state"]))(self.execute_adapter(summary,0)))

if __name__ == "__main__":
    unittest.main()
