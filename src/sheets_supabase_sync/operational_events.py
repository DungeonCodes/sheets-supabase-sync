from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class OperationalEvent:
    timestamp: datetime
    component: str
    operation: str
    outcome: str
    severity: Severity
    source_ref: str | None = None
    execution_id: str | None = None
    attempt: int | None = None
    max_attempts: int | None = None
    retryable: bool | None = None
    error_category: str | None = None
    error_code: str | None = None
    duration_ms: int | None = None
    backoff_ms: int | None = None

    @classmethod
    def create(cls, *, component: str, operation: str, outcome: str, severity: Severity, **fields: object) -> "OperationalEvent":
        return cls(datetime.now(UTC), component, operation, outcome, severity, **fields)

    def as_json(self) -> str:
        return json.dumps({key: value for key, value in asdict(self).items() if value is not None}, default=str, sort_keys=True)


_SENSITIVE = re.compile(r"(postgres(?:ql)?://\S+|https?://\S+|(?:token|password|secret|authorization)\s*[:=]\s*\S+)", re.I)


def safe_ref(value: str) -> str:
    return value[:12]


def sanitize_text(value: object) -> str:
    text = str(value)
    return "sensitive_detail_hidden" if _SENSITIVE.search(text) else text[:120]


def log_operational_event(logger: logging.Logger, event: OperationalEvent) -> None:
    logger.log(_log_level(event.severity), event.as_json())


def _log_level(severity: Severity) -> int:
    return {Severity.INFO: logging.INFO, Severity.WARNING: logging.WARNING, Severity.ERROR: logging.ERROR, Severity.CRITICAL: logging.CRITICAL}[severity]
