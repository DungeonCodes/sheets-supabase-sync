from __future__ import annotations

import csv
import unittest
from datetime import UTC, datetime
from pathlib import Path

from sheets_supabase_sync.batch import SourceStatus, summarize_outcomes, synchronize_independently
from sheets_supabase_sync.config import load_institution_config
from sheets_supabase_sync.errors import ErrorCode, SyncError
from sheets_supabase_sync.operational_events import OperationalEvent
from sheets_supabase_sync.raw_repository import InMemoryRawStateRepository
from sheets_supabase_sync.raw_sync import RawInputRow, RawSyncSource, build_raw_snapshot
from sheets_supabase_sync.raw_sync_service import RawSynchronizationService
from sheets_supabase_sync.retries import RetryPolicy


ROOT = Path(__file__).parents[2]
NOW = datetime(2026, 9, 2, tzinfo=UTC)


def load_fixture(name: str) -> tuple[tuple[str, ...], tuple[RawInputRow, ...]]:
    with (ROOT / "data" / "fixtures" / name).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ()), tuple(RawInputRow(index, row) for index, row in enumerate(reader, 2))


def raw_source(name: str, spreadsheet_id: str, sheet_name: str, target_table: str) -> RawSyncSource:
    return RawSyncSource(name, f"{name.lower()}-safe-ref", spreadsheet_id, sheet_name, target_table, ("registro_id",))


class MultiSourceDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        config = load_institution_config(ROOT / "configs" / "examples" / "multi-source.example.json")
        source_a, source_b = config.sources
        self.source_a = raw_source(source_a.name, source_a.spreadsheet_id, source_a.sheet_name, source_a.target_table)
        self.source_b = raw_source(source_b.name, source_b.spreadsheet_id, source_b.sheet_name, source_b.target_table)
        self.header_a, self.rows_a = load_fixture("multi_source_a.csv")
        self.header_b, self.rows_b = load_fixture("multi_source_b.csv")

    def test_two_configured_sources_have_distinct_schemas_and_shared_key_text(self) -> None:
        self.assertNotEqual(self.header_a, self.header_b)
        self.assertEqual("1001", self.rows_a[0].values["registro_id"])
        self.assertEqual("1001", self.rows_b[0].values["registro_id"])
        snapshot_a = build_raw_snapshot(self.source_a, self.header_a, self.rows_a, NOW)
        snapshot_b = build_raw_snapshot(self.source_b, self.header_b, self.rows_b, NOW)
        self.assertEqual(next(iter(snapshot_a.records)), next(iter(snapshot_b.records)))
        self.assertNotEqual(snapshot_a.snapshot_hash, snapshot_b.snapshot_hash)

    def test_state_idempotence_update_tombstone_restore_and_retry_are_source_scoped(self) -> None:
        repository = InMemoryRawStateRepository()
        execution_ids = iter(f"run-{index}" for index in range(20))
        service = RawSynchronizationService(
            repository,
            retry_policy=RetryPolicy(max_attempts=2, base_delay_seconds=0.01, max_delay_seconds=0.01, max_elapsed_seconds=1, jitter_ratio=0),
            pause=lambda _: None,
            random_value=lambda: 0,
            execution_id_factory=lambda: next(execution_ids),
        )
        service.persist_locally(self.source_a, self.header_a, self.rows_a, NOW)
        service.persist_locally(self.source_b, self.header_b, self.rows_b, NOW)
        before_b = repository.current_rows(self.source_b.source_hash)

        identical_a = service.persist_locally(self.source_a, self.header_a, self.rows_a, NOW)
        updated_a = list(self.rows_a)
        updated_a[0] = RawInputRow(2, {"registro_id": "1001", "curso": "curso_alpha", "status": "concluido"})
        service.persist_locally(self.source_a, self.header_a, tuple(updated_a), NOW)
        service.persist_locally(self.source_a, self.header_a, tuple(updated_a[:1]), NOW)
        service.persist_locally(self.source_a, self.header_a, tuple(updated_a), NOW)

        repository._faults["state"] = [SyncError(ErrorCode.DATABASE_TRANSIENT, "controlled", True)]
        retried_a = list(updated_a)
        retried_a[0] = RawInputRow(2, {"registro_id": "1001", "curso": "curso_alpha", "status": "revisado"})
        service.persist_locally(self.source_a, self.header_a, tuple(retried_a), NOW)

        self.assertEqual(2, identical_a.plan.counts["unchanged"])
        self.assertEqual(before_b, repository.current_rows(self.source_b.source_hash))
        self.assertEqual(3, repository.current_rows(self.source_a.source_hash)[next(iter(build_raw_snapshot(self.source_a, self.header_a, self.rows_a, NOW).records))].version)

    def test_batch_continues_and_returns_sanitized_aggregate(self) -> None:
        config = load_institution_config(ROOT / "configs" / "examples" / "multi-source.example.json")

        def run(source):
            if source.name == "SOURCE_A":
                raise SyncError(ErrorCode.SOURCE_INACTIVE, "password=private", False)
            return {"persisted": True}

        outcomes = synchronize_independently(list(config.sources), run)
        summary = summarize_outcomes(outcomes)
        self.assertEqual([SourceStatus.INACTIVE, SourceStatus.SUCCEEDED], [outcome.status for outcome in outcomes])
        self.assertEqual(
            {"sources_total": 2, "sources_succeeded": 1, "sources_failed": 0, "sources_busy": 0, "sources_inactive": 1},
            summary.as_dict(),
        )
        self.assertNotIn("private", outcomes[0].error or "")

    def test_batch_distinguishes_busy_failed_and_inactive(self) -> None:
        config = load_institution_config(ROOT / "configs" / "examples" / "multi-source.example.json")
        source_a, source_b = config.sources
        busy = synchronize_independently([source_a], lambda _: (_ for _ in ()).throw(SyncError(ErrorCode.BUSY, "busy")))
        failed = synchronize_independently([source_b], lambda _: (_ for _ in ()).throw(RuntimeError("controlled")))
        inactive = synchronize_independently([source_a], lambda _: (_ for _ in ()).throw(SyncError(ErrorCode.SOURCE_INACTIVE, "inactive")))
        summary = summarize_outcomes(busy + failed + inactive)
        self.assertEqual((0, 1, 1, 1), (summary.sources_succeeded, summary.sources_failed, summary.sources_busy, summary.sources_inactive))

    def test_observability_uses_distinct_safe_source_refs(self) -> None:
        events: list[OperationalEvent] = []
        for source, header, rows in (
            (self.source_a, self.header_a, self.rows_a),
            (self.source_b, self.header_b, self.rows_b),
        ):
            repository = InMemoryRawStateRepository(fail_on_start=True)
            service = RawSynchronizationService(repository, reporter=events.append)
            with self.assertRaises(SyncError):
                service.persist_locally(source, header, rows, NOW)
        refs = {event.source_ref for event in events}
        self.assertEqual({self.source_a.source_hash[:12], self.source_b.source_hash[:12]}, refs)
        self.assertEqual(2, len(refs))
        serialized = " ".join(event.as_json() for event in events)
        self.assertNotIn(self.source_a.spreadsheet_id, serialized)
        self.assertNotIn("curso_alpha", serialized)


if __name__ == "__main__":
    unittest.main()
