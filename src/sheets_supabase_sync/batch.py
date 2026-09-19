from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .errors import ErrorCode, SyncError, safe_error_message
from .sources import DataSource


class SourceStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BUSY = "busy"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class SourceOutcome:
    source_name: str
    succeeded: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    error_code: ErrorCode | None = None

    @property
    def status(self) -> SourceStatus:
        if self.succeeded:
            return SourceStatus.SUCCEEDED
        if self.error_code is ErrorCode.BUSY:
            return SourceStatus.BUSY
        if self.error_code is ErrorCode.SOURCE_INACTIVE:
            return SourceStatus.INACTIVE
        return SourceStatus.FAILED


@dataclass(frozen=True)
class BatchSummary:
    sources_total: int
    sources_succeeded: int
    sources_failed: int
    sources_busy: int
    sources_inactive: int

    def as_dict(self) -> dict[str, int]:
        return {
            "sources_total": self.sources_total,
            "sources_succeeded": self.sources_succeeded,
            "sources_failed": self.sources_failed,
            "sources_busy": self.sources_busy,
            "sources_inactive": self.sources_inactive,
        }


def synchronize_independently(sources: list[DataSource], run_source: Callable[[DataSource], dict[str, Any]]) -> list[SourceOutcome]:
    outcomes: list[SourceOutcome] = []
    for source in sources:
        try:
            outcomes.append(SourceOutcome(source.name, True, result=run_source(source)))
        except SyncError as error:
            outcomes.append(SourceOutcome(source.name, False, error=safe_error_message(error), error_code=error.code))
        except (ValueError, RuntimeError, OSError) as error:
            outcomes.append(SourceOutcome(source.name, False, error=safe_error_message(error)))
    return outcomes


def summarize_outcomes(outcomes: list[SourceOutcome]) -> BatchSummary:
    counts = {status: 0 for status in SourceStatus}
    for outcome in outcomes:
        counts[outcome.status] += 1
    return BatchSummary(
        sources_total=len(outcomes),
        sources_succeeded=counts[SourceStatus.SUCCEEDED],
        sources_failed=counts[SourceStatus.FAILED],
        sources_busy=counts[SourceStatus.BUSY],
        sources_inactive=counts[SourceStatus.INACTIVE],
    )
