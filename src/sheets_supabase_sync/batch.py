from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .sources import DataSource


@dataclass(frozen=True)
class SourceOutcome:
    source_name: str
    succeeded: bool
    result: dict[str, Any] | None = None
    error: str | None = None


def synchronize_independently(sources: list[DataSource], run_source: Callable[[DataSource], dict[str, Any]]) -> list[SourceOutcome]:
    outcomes: list[SourceOutcome] = []
    for source in sources:
        try:
            outcomes.append(SourceOutcome(source.name, True, result=run_source(source)))
        except (ValueError, RuntimeError, OSError) as error:
            outcomes.append(SourceOutcome(source.name, False, error=str(error)))
    return outcomes
