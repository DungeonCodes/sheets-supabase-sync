from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any

from .batch import SourceOutcome, synchronize_independently
from .scheduling import due_sources
from .sources import DataSource


def synchronize_one_source(source: DataSource, run_source: Callable[[DataSource], dict[str, Any]]) -> SourceOutcome:
    return synchronize_independently([source], run_source)[0]


def synchronize_due_sources(sources: Iterable[DataSource], now: datetime, run_source: Callable[[DataSource], dict[str, Any]]) -> list[SourceOutcome]:
    return synchronize_independently(due_sources(sources, now), run_source)
