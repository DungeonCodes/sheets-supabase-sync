from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from random import random
from time import monotonic, sleep
from typing import TypeVar

from .errors import SyncError

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 16.0
    max_elapsed_seconds: float = 45.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or min(self.base_delay_seconds, self.max_delay_seconds, self.max_elapsed_seconds) <= 0:
            raise ValueError("Politica de retry invalida")
        if not 0 <= self.jitter_ratio <= 1:
            raise ValueError("Jitter de retry invalido")


@dataclass(frozen=True)
class RetryNotice:
    attempt: int
    max_attempts: int
    error_code: str
    wait_seconds: float
    elapsed_seconds: float


def retry(
    operation: Callable[[], T],
    attempts: int = 3,
    pause: Callable[[float], None] = sleep,
    *,
    policy: RetryPolicy | None = None,
    random_value: Callable[[], float] = random,
    on_retry: Callable[[RetryNotice], None] | None = None,
    monotonic_clock: Callable[[], float] = monotonic,
) -> T:
    selected = policy or RetryPolicy(max_attempts=attempts, jitter_ratio=0)
    started = monotonic_clock()
    for attempt in range(1, selected.max_attempts + 1):
        try:
            return operation()
        except SyncError as error:
            if not error.retryable or attempt == selected.max_attempts:
                raise
            exponential = min(selected.max_delay_seconds, selected.base_delay_seconds * (2 ** (attempt - 1)))
            jitter = exponential * selected.jitter_ratio * random_value()
            wait_seconds = max(error.retry_after_seconds or 0, exponential + jitter)
            if monotonic_clock() - started + wait_seconds > selected.max_elapsed_seconds:
                raise
            if on_retry:
                on_retry(RetryNotice(attempt, selected.max_attempts, error.code.value, wait_seconds, monotonic_clock() - started))
            pause(wait_seconds)
    raise RuntimeError("Tentativas esgotadas")
