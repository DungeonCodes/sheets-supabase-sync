from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from pathlib import Path

from sheets_supabase_sync.environment import Environment
from sheets_supabase_sync.errors import ErrorCode, SyncError
from sheets_supabase_sync.executors import assert_local_url
from sheets_supabase_sync.google_sheets import SheetReadResult, SheetRow
from sheets_supabase_sync.raw_repository import InMemoryRawStateRepository
from sheets_supabase_sync.raw_sync import RawSyncSource
from sheets_supabase_sync.sources import DataSource, InstitutionConfig
from sheets_supabase_sync.staging_cli import run_cli
from sheets_supabase_sync.staging_guard import validate_staging_access
from sheets_supabase_sync.staging_sync import StagingSyncMode, StagingSyncOrchestrator


NOW = datetime(2026, 9, 9, tzinfo=UTC)
SOURCE = DataSource("forms_demo", "sheet-id", "Responses", "forms_demo_raw", ("registro_id",), 180)
RAW_SOURCE = RawSyncSource("forms_demo", "source-hash", "sheet-id", "Responses", "forms_demo_raw", ("registro_id",))


class FakeReader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    def read(self, spreadsheet_id: str, sheet_name: str, optional_range: str | None = None) -> SheetReadResult:
        self.calls.append((spreadsheet_id, sheet_name, optional_range))
        return SheetReadResult(
            sheet_name=sheet_name,
            sheet_count=1,
            header=("registro_id", "categoria", "pontuacao"),
            normalized_header=("registro_id", "categoria", "pontuacao"),
            rows=(
                SheetRow(2, ("DEMO-001", "A", "10")),
                SheetRow(3, ("DEMO-002", "B", "20")),
                SheetRow(4, ("DEMO-003", "C", "30")),
            ),
            empty_rows_ignored=0,
            read_at=NOW,
            source_hash="source-hash",
            retry_count=0,
            duration_ms=5,
        )


def environment(app_env: str = "staging", *, matching_ref: bool = True) -> Environment:
    project_ref = "safe-project"
    allowed = project_ref if matching_ref else "other-project"
    return Environment(
        app_env,
        project_ref,
        allowed,
        f"https://{project_ref}.supabase.co",
        f"postgresql://postgres.{project_ref}:redacted@aws-0-region.pooler.supabase.com:5432/postgres",
        "redacted-secret",
        "C:/outside/credential.json",
    )


class StagingSyncCoreTests(unittest.TestCase):
    def test_core_composes_google_snapshot_and_existing_repository(self) -> None:
        reader = FakeReader()
        repository = InMemoryRawStateRepository()
        result = StagingSyncOrchestrator(reader, repository).run(SOURCE, StagingSyncMode.APPLY_STAGING)
        self.assertEqual([("sheet-id", "Responses", None)], reader.calls)
        self.assertTrue(result.persisted)
        self.assertEqual(3, result.plan.counts["new"])
        self.assertEqual(3, len(repository.current_rows("source-hash")))
        self.assertEqual(3, len(repository.history()))

    def test_dry_run_reads_previous_snapshot_without_writes(self) -> None:
        reader = FakeReader()
        repository = InMemoryRawStateRepository()
        result = StagingSyncOrchestrator(reader, repository).run(SOURCE, StagingSyncMode.DRY_RUN)
        self.assertFalse(result.persisted)
        self.assertEqual(0, result.metrics.rows_persisted)
        self.assertEqual(0, repository._source_writes)
        self.assertEqual(0, len(repository.history()))
        self.assertEqual({}, repository.current_rows("source-hash"))

    def test_existing_compatible_source_is_accepted_without_registration_write(self) -> None:
        repository = InMemoryRawStateRepository(existing_sources=((RAW_SOURCE, True),))
        result = StagingSyncOrchestrator(FakeReader(), repository).run(SOURCE, StagingSyncMode.APPLY_STAGING)
        self.assertTrue(result.persisted)
        self.assertEqual(0, repository._source_writes)

    def test_existing_incompatible_source_fails_closed_without_writes(self) -> None:
        incompatible = RawSyncSource("forms_demo", "source-hash", "sheet-id", "Responses", "other_raw", ("registro_id",))
        repository = InMemoryRawStateRepository(existing_sources=((incompatible, True),))
        with self.assertRaises(SyncError) as raised:
            StagingSyncOrchestrator(FakeReader(), repository).run(SOURCE, StagingSyncMode.APPLY_STAGING)
        self.assertEqual(ErrorCode.SOURCE_MISMATCH, raised.exception.code)
        self.assertEqual(0, repository._source_writes)
        self.assertEqual(0, len(repository.history()))
        self.assertEqual([], repository._started_execution_ids)

    def test_configured_inactive_source_stops_before_google_or_repository(self) -> None:
        reader = FakeReader()
        repository = InMemoryRawStateRepository()
        inactive = DataSource("forms_demo", "sheet-id", "Responses", "forms_demo_raw", ("registro_id",), 180, enabled=False)
        with self.assertRaises(SyncError) as raised:
            StagingSyncOrchestrator(reader, repository).run(inactive, StagingSyncMode.APPLY_STAGING)
        self.assertEqual(ErrorCode.SOURCE_INACTIVE, raised.exception.code)
        self.assertEqual([], reader.calls)
        self.assertEqual(0, repository._source_writes)

    def test_persisted_inactive_source_stops_before_sync_writes(self) -> None:
        repository = InMemoryRawStateRepository(existing_sources=((RAW_SOURCE, False),))
        with self.assertRaises(SyncError) as raised:
            StagingSyncOrchestrator(FakeReader(), repository).run(SOURCE, StagingSyncMode.APPLY_STAGING)
        self.assertEqual(ErrorCode.SOURCE_INACTIVE, raised.exception.code)
        self.assertEqual(0, repository._source_writes)
        self.assertEqual(0, len(repository.history()))
        self.assertEqual([], repository._started_execution_ids)

    def test_busy_source_is_deferred_without_writes(self) -> None:
        repository = InMemoryRawStateRepository()
        self.assertTrue(repository.try_acquire("source-hash"))
        with self.assertRaises(SyncError) as raised:
            StagingSyncOrchestrator(FakeReader(), repository).run(SOURCE, StagingSyncMode.APPLY_STAGING)
        self.assertEqual(ErrorCode.BUSY, raised.exception.code)
        self.assertEqual(0, repository._source_writes)
        self.assertEqual([], repository._started_execution_ids)

    def test_second_identical_sync_is_idempotent(self) -> None:
        repository = InMemoryRawStateRepository()
        orchestrator = StagingSyncOrchestrator(FakeReader(), repository)
        orchestrator.run(SOURCE, StagingSyncMode.APPLY_STAGING)
        second = orchestrator.run(SOURCE, StagingSyncMode.APPLY_STAGING)
        self.assertEqual(3, second.plan.counts["unchanged"])
        self.assertEqual(0, second.metrics.rows_persisted)
        self.assertEqual(3, len(repository.history()))


class StagingGuardTests(unittest.TestCase):
    def test_staging_write_requires_explicit_confirmation(self) -> None:
        with self.assertRaises(SyncError):
            validate_staging_access(environment(), write_requested=True, confirmed=False)
        validate_staging_access(environment(), write_requested=True, confirmed=True)

    def test_production_is_always_rejected(self) -> None:
        for confirmed in (False, True):
            with self.assertRaises(SyncError):
                validate_staging_access(environment("production"), write_requested=True, confirmed=confirmed)

    def test_unknown_environment_is_rejected(self) -> None:
        with self.assertRaises(SyncError):
            validate_staging_access(environment("qa"), write_requested=False, confirmed=False)
        with self.assertRaises(SyncError):
            validate_staging_access(environment(matching_ref=False), write_requested=True, confirmed=True)

    def test_database_target_must_match_the_allowed_project(self) -> None:
        target = environment()
        mismatched = Environment(
            target.app_env,
            target.project_ref,
            target.allowed_ref,
            target.supabase_url,
            "postgresql://postgres.other-project:redacted@aws-0-region.pooler.supabase.com:5432/postgres",
            target.secret_key,
            target.google_file,
        )
        with self.assertRaises(SyncError):
            validate_staging_access(mismatched, write_requested=True, confirmed=True)

    def test_apply_local_remains_blocked_for_remote_hosts(self) -> None:
        with self.assertRaises(ValueError):
            assert_local_url("postgresql://redacted@pooler.example.test:5432/postgres")


class StagingCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = InstitutionConfig("demo", "isolated", (SOURCE,))
        self.outputs: list[str] = []
        self.calls: list[StagingSyncMode] = []

    def execute(self, arguments: list[str], selected_environment: Environment | None = None, operation=None) -> int:
        def successful_operation(root, env, source, mode):
            self.calls.append(mode)
            return StagingSyncOrchestrator(FakeReader(), InMemoryRawStateRepository()).run(source, mode)

        return run_cli(
            arguments,
            root=Path("C:/repository"),
            environment_loader=lambda _: selected_environment or environment(),
            institution_loader=lambda _: self.config,
            operation=operation or successful_operation,
            emit=self.outputs.append,
        )

    def test_entrypoint_rejects_unconfirmed_staging_before_operation(self) -> None:
        code = self.execute(["--config", "config.json", "--source", "forms_demo", "--mode", "apply-staging"])
        self.assertEqual(2, code)
        self.assertEqual([], self.calls)

    def test_entrypoint_allows_confirmed_staging(self) -> None:
        code = self.execute(["--config", "config.json", "--source", "forms_demo", "--mode", "apply-staging", "--confirm-staging"])
        self.assertEqual(0, code)
        self.assertEqual([StagingSyncMode.APPLY_STAGING], self.calls)

    def test_entrypoint_rejects_production_before_operation(self) -> None:
        code = self.execute(
            ["--config", "config.json", "--source", "forms_demo", "--mode", "apply-staging", "--confirm-staging"],
            selected_environment=environment("production"),
        )
        self.assertEqual(2, code)
        self.assertEqual([], self.calls)

    def test_output_is_operational_and_sanitized(self) -> None:
        def failure(root, env, source, mode):
            raise SyncError(ErrorCode.DATABASE, "postgresql://user:password@secret-host/private-cell")

        code = self.execute(["--config", "config.json", "--source", "forms_demo"], operation=failure)
        rendered = " ".join(self.outputs)
        self.assertEqual(2, code)
        self.assertNotIn("password", rendered)
        self.assertNotIn("secret-host", rendered)
        self.assertNotIn("private-cell", rendered)
        self.assertEqual({"category": "database", "status": "failed"}, json.loads(rendered))

    def test_unexpected_error_output_is_sanitized(self) -> None:
        def failure(root, env, source, mode):
            raise RuntimeError("private_key=secret-value")

        code = self.execute(["--config", "config.json", "--source", "forms_demo"], operation=failure)
        rendered = " ".join(self.outputs)
        self.assertEqual(2, code)
        self.assertNotIn("private_key", rendered)
        self.assertNotIn("secret-value", rendered)
        self.assertEqual({"category": "internal", "status": "failed"}, json.loads(rendered))

    def test_new_modules_have_no_docker_dependency(self) -> None:
        package = Path(__file__).parents[2] / "src" / "sheets_supabase_sync"
        content = (package / "staging_sync.py").read_text(encoding="utf-8") + (package / "staging_cli.py").read_text(encoding="utf-8")
        self.assertNotIn("docker", content.lower())
        self.assertNotIn("forms_demo", content)


if __name__ == "__main__":
    unittest.main()
