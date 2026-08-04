from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from .sources import DataSource


def due_sources(sources: Iterable[DataSource], now: datetime) -> list[DataSource]:
    return [source for source in sources if source.enabled and (source.last_sync_at is None or source.next_sync_at() <= now)]
