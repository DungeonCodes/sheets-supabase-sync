from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    QUOTA = "quota"
    TIMEOUT = "timeout"
    TRANSIENT = "transient"
    SCHEMA = "schema"
    VALIDATION = "validation"
    DATABASE = "database"
    INTERNAL = "internal"


@dataclass(frozen=True)
class SyncError(Exception):
    code: ErrorCode
    message: str
    retryable: bool = False


def classify_http_error(status_code: int) -> SyncError:
    mapping = {401: (ErrorCode.AUTHENTICATION, False), 403: (ErrorCode.AUTHORIZATION, False), 404: (ErrorCode.NOT_FOUND, False), 429: (ErrorCode.QUOTA, True), 500: (ErrorCode.TRANSIENT, True), 503: (ErrorCode.TRANSIENT, True)}
    code, retryable = mapping.get(status_code, (ErrorCode.INTERNAL, False))
    return SyncError(code, f"Erro de origem classificado: {code}", retryable)


def safe_error_message(error: BaseException) -> str:
    text = str(error)
    for marker in ("postgresql://", "password=", "service_role", "token="):
        if marker in text.lower():
            return "Erro sensivel ocultado"
    return text[:300]
