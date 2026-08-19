from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .errors import ErrorCode, SyncError


class FailureDisposition(StrEnum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    BUSY_DEFERRED = "busy_deferred"
    AMBIGUOUS_OUTCOME = "ambiguous_outcome"


class DatabaseStage(StrEnum):
    CONNECT = "connect"
    TRANSACTION = "transaction"
    BEFORE_COMMIT = "before_commit"
    COMMIT = "commit"


@dataclass(frozen=True)
class FailureDecision:
    category: str
    disposition: FailureDisposition
    sqlstate: str | None = None

    @property
    def retryable(self) -> bool:
        return self.disposition is FailureDisposition.RETRYABLE


_TRANSACTION_RETRY_SQLSTATES = frozenset({"40001", "40P01"})
_AUTHENTICATION_SQLSTATE_PREFIXES = ("28",)
_CONFIGURATION_SQLSTATE_PREFIXES = ("3D", "42")


def classify_postgres_failure(error: BaseException, stage: DatabaseStage) -> FailureDecision:
    """Classifica falhas sem depender de texto potencialmente sensivel do driver."""
    sqlstate = getattr(error, "sqlstate", None)
    if isinstance(sqlstate, str):
        if sqlstate.startswith(_AUTHENTICATION_SQLSTATE_PREFIXES):
            return FailureDecision("authentication", FailureDisposition.NON_RETRYABLE, sqlstate)
        if sqlstate.startswith(_CONFIGURATION_SQLSTATE_PREFIXES):
            return FailureDecision("configuration_or_schema", FailureDisposition.NON_RETRYABLE, sqlstate)
        if sqlstate in _TRANSACTION_RETRY_SQLSTATES:
            return FailureDecision("transaction_conflict", FailureDisposition.RETRYABLE, sqlstate)
        if sqlstate.startswith("08"):
            return _connection_decision(stage, sqlstate)
    if isinstance(error, TimeoutError):
        return _connection_decision(stage, sqlstate, "connection_timeout")
    if isinstance(error, (ConnectionError, OSError)):
        return _connection_decision(stage, sqlstate)
    return FailureDecision("database_permanent_or_unknown", FailureDisposition.NON_RETRYABLE, sqlstate)


def busy_decision() -> FailureDecision:
    return FailureDecision("advisory_lock_busy", FailureDisposition.BUSY_DEFERRED)


def postgres_sync_error(error: BaseException, stage: DatabaseStage) -> SyncError:
    decision = classify_postgres_failure(error, stage)
    code = {
        FailureDisposition.RETRYABLE: ErrorCode.DATABASE_TRANSIENT,
        FailureDisposition.NON_RETRYABLE: ErrorCode.DATABASE,
        FailureDisposition.BUSY_DEFERRED: ErrorCode.BUSY,
        FailureDisposition.AMBIGUOUS_OUTCOME: ErrorCode.AMBIGUOUS_OUTCOME,
    }[decision.disposition]
    return SyncError(code, f"Falha PostgreSQL classificada: {decision.category}", decision.retryable)


def _connection_decision(
    stage: DatabaseStage,
    sqlstate: str | None,
    category: str = "connection",
) -> FailureDecision:
    if stage is DatabaseStage.COMMIT:
        return FailureDecision("ambiguous_commit", FailureDisposition.AMBIGUOUS_OUTCOME, sqlstate)
    return FailureDecision(category, FailureDisposition.RETRYABLE, sqlstate)
