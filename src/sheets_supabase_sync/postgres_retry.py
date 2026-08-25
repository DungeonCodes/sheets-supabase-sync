from __future__ import annotations

import logging
from collections.abc import Callable
from random import random
from time import monotonic, sleep
from typing import TypeVar

from .operational_failures import DatabaseStage, postgres_sync_error
from .observability import log_event
from .retries import RetryNotice, RetryPolicy, retry


ConnectionT = TypeVar("ConnectionT")


def connect_with_retry(
    connect: Callable[[], ConnectionT],
    *,
    source_prefix: str,
    policy: RetryPolicy = RetryPolicy(max_attempts=3, base_delay_seconds=0.25, max_delay_seconds=2, max_elapsed_seconds=8),
    pause: Callable[[float], None] = sleep,
    random_value: Callable[[], float] = random,
    monotonic_clock: Callable[[], float] = monotonic,
    logger: logging.Logger | None = None,
) -> ConnectionT:
    """Repete somente a abertura da conexao, antes de qualquer transacao ou mutacao."""
    selected_logger = logger or logging.getLogger(__name__)

    def attempt() -> ConnectionT:
        try:
            return connect()
        except Exception as error:
            raise postgres_sync_error(error, DatabaseStage.CONNECT) from error

    def on_retry(notice: RetryNotice) -> None:
        log_event(
            selected_logger,
            "postgres_connect_retry",
            data_source_id=source_prefix[:12],
            operation="postgres_connect",
            attempt=notice.attempt,
            max_attempts=notice.max_attempts,
            error_category=notice.error_code,
            retryable=True,
            backoff_ms=round(notice.wait_seconds * 1000),
            duration_ms=round(notice.elapsed_seconds * 1000),
            outcome="retrying",
        )

    return retry(
        attempt,
        policy=policy,
        pause=pause,
        random_value=random_value,
        on_retry=on_retry,
        monotonic_clock=monotonic_clock,
    )
