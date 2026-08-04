from __future__ import annotations

from collections.abc import Callable
from time import sleep
from typing import TypeVar

from .errors import SyncError

T = TypeVar("T")


def retry(operation: Callable[[], T], attempts: int = 3, pause: Callable[[float], None] = sleep) -> T:
    for attempt in range(attempts):
        try:
            return operation()
        except SyncError as error:
            if not error.retryable or attempt == attempts - 1:
                raise
            pause(2**attempt)
    raise RuntimeError("Tentativas esgotadas")
