from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from .batch import SourceOutcome, SourceStatus, synchronize_independently
from .errors import ErrorCode, SyncError
from .raw_sync_service import RawSyncResult
from .sources import DataSource


class SelectionStatus(StrEnum):
    DUE = "due"
    NOT_DUE = "not_due"
    INACTIVE = "inactive"
    INVALID = "invalid"


@dataclass(frozen=True)
class OperationalSource:
    name: str
    spreadsheet_id: str
    sheet_name: str
    target_table: str
    business_key: tuple[str, ...]
    enabled: bool
    lifecycle_status: str
    last_sync_at: datetime | None


@dataclass(frozen=True)
class SourceSelection:
    source: DataSource
    status: SelectionStatus


@dataclass(frozen=True)
class DispatchSummary:
    sources_total: int
    sources_due: int
    sources_executed: int
    sources_no_changes: int
    sources_skipped: int
    sources_busy_deferred: int
    sources_failed: int

    def as_dict(self) -> dict[str, int]:
        return {
            "sources_total": self.sources_total,
            "sources_due": self.sources_due,
            "sources_executed": self.sources_executed,
            "sources_no_changes": self.sources_no_changes,
            "sources_skipped": self.sources_skipped,
            "sources_busy_deferred": self.sources_busy_deferred,
            "sources_failed": self.sources_failed,
        }


class OperationalStateLoader(Protocol):
    def __call__(self, sources: Sequence[DataSource]) -> dict[str, OperationalSource]: ...


def load_operational_sources(database_url: str, sources: Sequence[DataSource]) -> dict[str, OperationalSource]:
    """Read only operational state; successful sync time is derived from sync_runs."""
    if not sources:
        return {}
    names = [source.name for source in sources]
    try:
        import psycopg

        with psycopg.connect(database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(_operational_sources_sql(), (names,))
                rows = cursor.fetchall()
            connection.rollback()
    except Exception as error:
        raise SyncError(ErrorCode.DATABASE, "Estado operacional indisponivel") from error
    return {
        row[0]: OperationalSource(row[0], row[1], row[2], row[3], tuple(row[4] or ()), row[5], row[6], row[7])
        for row in rows
    }


def select_sources_due(
    sources: Sequence[DataSource],
    operational_sources: dict[str, OperationalSource],
    now: datetime,
) -> list[SourceSelection]:
    selections: list[SourceSelection] = []
    for source in sources:
        state = operational_sources.get(source.name)
        if state is None or not _matches_config(source, state):
            selections.append(SourceSelection(source, SelectionStatus.INVALID))
        elif not source.enabled or not state.enabled or state.lifecycle_status != "active":
            selections.append(SourceSelection(source, SelectionStatus.INACTIVE))
        elif state.last_sync_at is None or state.last_sync_at + timedelta(minutes=source.sync_interval_minutes) <= now:
            selections.append(SourceSelection(source, SelectionStatus.DUE))
        else:
            selections.append(SourceSelection(source, SelectionStatus.NOT_DUE))
    return selections


def dispatch_sources(
    selections: Sequence[SourceSelection],
    run_source: Callable[[DataSource], RawSyncResult],
) -> tuple[list[SourceOutcome], DispatchSummary]:
    due = [selection.source for selection in selections if selection.status is SelectionStatus.DUE]
    outcomes = synchronize_independently(due, lambda source: _result_as_dict(run_source(source)))
    return outcomes, summarize_dispatch(selections, outcomes)


def summarize_dispatch(selections: Sequence[SourceSelection], outcomes: Sequence[SourceOutcome]) -> DispatchSummary:
    due = sum(selection.status is SelectionStatus.DUE for selection in selections)
    no_changes = sum(
        outcome.succeeded and _has_no_changes(outcome.result)
        for outcome in outcomes
    )
    return DispatchSummary(
        sources_total=len(selections),
        sources_due=due,
        sources_executed=len(outcomes),
        sources_no_changes=no_changes,
        sources_skipped=sum(selection.status in {SelectionStatus.NOT_DUE, SelectionStatus.INACTIVE} for selection in selections),
        sources_busy_deferred=sum(outcome.status is SourceStatus.BUSY for outcome in outcomes),
        sources_failed=(sum(selection.status is SelectionStatus.INVALID for selection in selections) + sum(outcome.status is SourceStatus.FAILED for outcome in outcomes)),
    )


def source_statuses(selections: Sequence[SourceSelection], outcomes: Sequence[SourceOutcome]) -> list[dict[str, str]]:
    outcomes_by_name = {outcome.source_name: outcome for outcome in outcomes}
    statuses: list[dict[str, str]] = []
    for selection in selections:
        if selection.status is SelectionStatus.NOT_DUE:
            status = "skipped_not_due"
        elif selection.status is SelectionStatus.INACTIVE:
            status = "skipped_inactive"
        elif selection.status is SelectionStatus.INVALID:
            status = "failed"
        else:
            outcome = outcomes_by_name.get(selection.source.name)
            status = "due" if outcome is None else _outcome_status(outcome)
        statuses.append({"source": selection.source.name, "status": status})
    return statuses


def _result_as_dict(result: RawSyncResult) -> dict[str, Any]:
    return {"counts": result.plan.counts, "persisted": result.persisted}


def _has_no_changes(result: dict[str, Any] | None) -> bool:
    if result is None:
        return False
    counts = result.get("counts")
    if not isinstance(counts, dict):
        return False
    return all(counts.get(kind, 0) == 0 for kind in ("new", "changed", "removed", "restored"))


def _outcome_status(outcome: SourceOutcome) -> str:
    if outcome.status is SourceStatus.BUSY:
        return "busy_deferred"
    if outcome.status is SourceStatus.INACTIVE:
        return "skipped_inactive"
    if outcome.status is SourceStatus.FAILED:
        return "failed"
    return "no_changes" if _has_no_changes(outcome.result) else "applied"


def _matches_config(source: DataSource, state: OperationalSource) -> bool:
    return (
        source.spreadsheet_id == state.spreadsheet_id
        and source.sheet_name == state.sheet_name
        and source.target_table == state.target_table
        and source.business_key == state.business_key
    )


def _operational_sources_sql() -> str:
    return (
        "WITH last_successful_run AS ("
        " SELECT data_source_id, max(finished_at) AS last_sync_at"
        " FROM public.sync_runs WHERE status = 'applied' AND finished_at IS NOT NULL"
        " GROUP BY data_source_id"
        ") "
        "SELECT data_sources.name, data_sources.spreadsheet_id, data_sources.sheet_name, "
        "data_sources.target_table, data_sources.business_key, data_sources.enabled, "
        "data_sources.lifecycle_status, last_successful_run.last_sync_at "
        "FROM public.data_sources "
        "LEFT JOIN last_successful_run ON last_successful_run.data_source_id = data_sources.id "
        "WHERE data_sources.name = ANY(%s)"
    )
