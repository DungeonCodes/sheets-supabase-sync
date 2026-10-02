from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sheets_supabase_sync.batch import SourceOutcome
from sheets_supabase_sync.batch_cli import run_cli
from sheets_supabase_sync.dispatcher import OperationalSource, SelectionStatus, select_sources_due, summarize_dispatch
from sheets_supabase_sync.environment import Environment
from sheets_supabase_sync.errors import ErrorCode, SyncError
from sheets_supabase_sync.sources import DataSource, InstitutionConfig


NOW = datetime(2026, 10, 2, 12, tzinfo=UTC)


def source(name: str, **kwargs: object) -> DataSource:
    return DataSource(name, f"sheet-{name}", "Responses", f"{name}_raw", ("id",), 180, **kwargs)


def state(configured: DataSource, **kwargs: object) -> OperationalSource:
    values = {
        "name": configured.name,
        "spreadsheet_id": configured.spreadsheet_id,
        "sheet_name": configured.sheet_name,
        "target_table": configured.target_table,
        "business_key": configured.business_key,
        "enabled": True,
        "lifecycle_status": "active",
        "last_sync_at": None,
    }
    values.update(kwargs)
    return OperationalSource(**values)  # type: ignore[arg-type]


def environment() -> Environment:
    return Environment(
        "staging", "safe-project", "safe-project", "https://safe-project.supabase.co",
        "postgresql://postgres.safe-project:redacted@aws-0-region.pooler.supabase.com:5432/postgres",
        "redacted", "credential.json",
    )


class DueSelectionTests(unittest.TestCase):
    def test_never_run_source_is_due(self) -> None:
        configured = source("new")
        selection = select_sources_due((configured,), {configured.name: state(configured)}, NOW)
        self.assertEqual([SelectionStatus.DUE], [item.status for item in selection])

    def test_interval_is_respected(self) -> None:
        configured = source("recent")
        recent = state(configured, last_sync_at=NOW - timedelta(minutes=179))
        expired = state(configured, last_sync_at=NOW - timedelta(minutes=180))
        self.assertEqual(SelectionStatus.NOT_DUE, select_sources_due((configured,), {configured.name: recent}, NOW)[0].status)
        self.assertEqual(SelectionStatus.DUE, select_sources_due((configured,), {configured.name: expired}, NOW)[0].status)

    def test_disabled_and_blocked_lifecycle_are_skipped(self) -> None:
        disabled = source("disabled", enabled=False)
        blocked = source("blocked")
        states = {
            disabled.name: state(disabled),
            blocked.name: state(blocked, lifecycle_status="suspended", enabled=False),
        }
        selections = select_sources_due((disabled, blocked), states, NOW)
        self.assertEqual([SelectionStatus.INACTIVE, SelectionStatus.INACTIVE], [item.status for item in selections])

    def test_remote_mismatch_is_invalid(self) -> None:
        configured = source("mismatch")
        remote = state(configured, target_table="other_raw")
        self.assertEqual(SelectionStatus.INVALID, select_sources_due((configured,), {configured.name: remote}, NOW)[0].status)

    def test_summary_distinguishes_busy_failure_and_no_changes(self) -> None:
        due = source("due")
        skipped = source("skipped")
        selections = select_sources_due(
            (due, skipped),
            {due.name: state(due), skipped.name: state(skipped, last_sync_at=NOW)},
            NOW,
        )
        outcomes = (
            SourceOutcome("due", True, result={"counts": {"new": 0, "changed": 0, "removed": 0, "restored": 0}}),
            SourceOutcome("other", False, error_code=ErrorCode.BUSY),
            SourceOutcome("bad", False, error_code=ErrorCode.DATABASE),
        )
        summary = summarize_dispatch(selections, outcomes)
        self.assertEqual(
            {"sources_total": 2, "sources_due": 1, "sources_executed": 3, "sources_no_changes": 1, "sources_skipped": 1, "sources_busy_deferred": 1, "sources_failed": 1},
            summary.as_dict(),
        )


class BatchCliTests(unittest.TestCase):
    def test_dry_selection_is_zero_write_and_does_not_run_sources(self) -> None:
        configured = source("one")
        config = InstitutionConfig("fixture", "isolated", (configured,))
        outputs: list[str] = []
        writes: list[str] = []
        code = run_cli(
            ["--config", "fixture.json", "--dry-select"],
            root=Path("repository"),
            environment_loader=lambda _: environment(),
            institution_loader=lambda _: config,
            state_loader=lambda _, sources: {configured.name: state(configured)},
            operation=lambda *_: writes.append("write"),  # type: ignore[return-value]
            now=lambda: NOW,
            emit=outputs.append,
        )
        self.assertEqual(0, code)
        self.assertEqual([], writes)
        self.assertEqual(
            {"environment": "staging", "mode": "dry_select", "sources": [{"source": "one", "status": "due"}], "sources_busy_deferred": 0, "sources_due": 1, "sources_executed": 0, "sources_failed": 0, "sources_no_changes": 0, "sources_skipped": 0, "sources_total": 1, "status": "selected"},
            json.loads(outputs[0]),
        )

    def test_a_failing_source_does_not_prevent_the_next_due_source(self) -> None:
        first, second = source("first"), source("second")
        config = InstitutionConfig("fixture", "isolated", (first, second))
        outputs: list[str] = []
        executed: list[str] = []

        def operation(_, __, configured, ___):
            executed.append(configured.name)
            if configured.name == "first":
                raise SyncError(ErrorCode.DATABASE, "controlled")
            return type("Result", (), {"plan": type("Plan", (), {"counts": {"new": 1, "changed": 0, "removed": 0, "restored": 0}})(), "persisted": True})()

        code = run_cli(
            ["--config", "fixture.json", "--confirm-staging"],
            root=Path("repository"), environment_loader=lambda _: environment(), institution_loader=lambda _: config,
            state_loader=lambda _, sources: {item.name: state(item) for item in sources}, operation=operation, now=lambda: NOW, emit=outputs.append,
        )
        self.assertEqual(0, code)
        self.assertEqual(["first", "second"], executed)
        self.assertEqual(1, json.loads(outputs[0])["sources_failed"])


if __name__ == "__main__":
    unittest.main()
