from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum, StrEnum

from .errors import ErrorCode


class HealthStatus(IntEnum):
    OK = 0
    WARNING = 1
    FAILURE = 2


class AlertSeverity(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class SourceHealth:
    enabled: bool
    interval_minutes: int
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    consecutive_failures: int = 0
    last_error_code: ErrorCode | None = None
    active_since: datetime | None = None


@dataclass(frozen=True)
class Alert:
    severity: AlertSeverity
    message: str


def alerts_for(health: SourceHealth, now: datetime) -> tuple[Alert, ...]:
    if not health.enabled:
        return ()
    alerts: list[Alert] = []
    if health.last_error_code in {ErrorCode.AUTHENTICATION, ErrorCode.AUTHORIZATION}:
        alerts.append(Alert(AlertSeverity.CRITICAL, "Autenticacao ou permissao invalida"))
    elif health.consecutive_failures >= 3:
        alerts.append(Alert(AlertSeverity.CRITICAL, "Tres falhas consecutivas"))
    elif health.consecutive_failures == 1:
        alerts.append(Alert(AlertSeverity.WARNING, "Primeira falha transitoria"))
    if health.last_success_at is None and health.active_since is not None:
        alerts.append(Alert(AlertSeverity.WARNING, "Nenhuma execucao bem-sucedida registrada"))
    elif health.last_success_at and now - health.last_success_at > timedelta(minutes=health.interval_minutes + 90):
        alerts.append(Alert(AlertSeverity.CRITICAL, "Ultimo sucesso excede a tolerancia"))
    return tuple(alerts)
