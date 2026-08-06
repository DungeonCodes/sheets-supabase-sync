from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    CONFIGURATION = "configuration"
    CREDENTIAL_MISSING = "credential_missing"
    CREDENTIAL_INVALID = "credential_invalid"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    SHEET_NOT_FOUND = "sheet_not_found"
    QUOTA = "quota"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    NETWORK = "network"
    RESPONSE = "response"
    TRANSIENT = "transient"
    SCHEMA = "schema"
    EMPTY_SHEET = "empty_sheet"
    VALIDATION = "validation"
    DATABASE = "database"
    INTERNAL = "internal"


@dataclass(frozen=True)
class SyncError(Exception):
    code: ErrorCode
    message: str
    retryable: bool = False
    retry_after_seconds: float | None = None


def classify_http_error(status_code: int, retry_after_seconds: float | None = None) -> SyncError:
    mapping = {400: (ErrorCode.RESPONSE, False), 401: (ErrorCode.AUTHENTICATION, False), 403: (ErrorCode.AUTHORIZATION, False), 404: (ErrorCode.NOT_FOUND, False), 429: (ErrorCode.QUOTA, True), 500: (ErrorCode.TRANSIENT, True), 502: (ErrorCode.TRANSIENT, True), 503: (ErrorCode.TRANSIENT, True), 504: (ErrorCode.TRANSIENT, True)}
    code, retryable = mapping.get(status_code, (ErrorCode.INTERNAL, False))
    return SyncError(code, f"Erro de origem classificado: {code}", retryable, retry_after_seconds)


def safe_error_message(error: BaseException) -> str:
    text = str(error)
    for marker in ("postgresql://", "password=", "service_role", "token=", "private_key", "access_token", "refresh_token"):
        if marker in text.lower():
            return "Erro sensivel ocultado"
    return text[:300]
