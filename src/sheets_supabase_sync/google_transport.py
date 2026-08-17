from __future__ import annotations

from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .errors import ErrorCode, SyncError, classify_http_error
from .google_config import SHEETS_READONLY_SCOPE

SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


class GoogleHttpTransport:
    def __init__(self, credential_file: Path) -> None:
        try:
            import requests
            from google.auth.exceptions import GoogleAuthError
            from google.auth.transport.requests import AuthorizedSession
            from google.oauth2.service_account import Credentials

            credentials = Credentials.from_service_account_file(str(credential_file), scopes=[SHEETS_READONLY_SCOPE])
            self._session = AuthorizedSession(credentials)
            self._google_auth_error = GoogleAuthError
            self._requests = requests
        except ImportError as error:
            raise SyncError(ErrorCode.CONFIGURATION, "Dependencia google-auth indisponivel") from error
        except (OSError, ValueError) as error:
            raise SyncError(ErrorCode.CREDENTIAL_INVALID, "Credencial Google rejeitada localmente") from error

    def get_metadata(self, spreadsheet_id: str, timeout_seconds: float) -> dict[str, Any]:
        url = f"{SHEETS_API_BASE}/{quote(spreadsheet_id, safe='')}"
        params = {"includeGridData": "false", "fields": "sheets.properties(sheetId,title,index,gridProperties(rowCount,columnCount))"}
        return self._get_json(url, params, timeout_seconds)

    def get_values(self, spreadsheet_id: str, sheet_range: str, timeout_seconds: float) -> dict[str, Any]:
        url = f"{SHEETS_API_BASE}/{quote(spreadsheet_id, safe='')}/values/{quote(sheet_range, safe='')}"
        params = {"majorDimension": "ROWS", "valueRenderOption": "FORMATTED_VALUE", "dateTimeRenderOption": "FORMATTED_STRING"}
        return self._get_json(url, params, timeout_seconds)

    def _get_json(self, url: str, params: dict[str, str], timeout_seconds: float) -> dict[str, Any]:
        try:
            response = self._session.get(url, params=params, timeout=timeout_seconds)
        except self._google_auth_error as error:
            raise SyncError(ErrorCode.AUTHENTICATION, "Autenticacao Google rejeitada") from error
        except self._requests.Timeout as error:
            raise SyncError(ErrorCode.TIMEOUT, "Timeout temporario na Google Sheets API", True) from error
        except self._requests.ConnectionError as error:
            raise SyncError(ErrorCode.NETWORK, "Falha temporaria de rede na Google Sheets API", True) from error
        except self._requests.RequestException as error:
            raise SyncError(ErrorCode.NETWORK, "Falha de rede na Google Sheets API") from error
        if not response.ok:
            retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
            if response.status_code == 403 and _is_quota_response(response):
                raise SyncError(ErrorCode.QUOTA, "Quota Google Sheets excedida", True, retry_after)
            raise classify_http_error(response.status_code, retry_after)
        try:
            payload = response.json()
        except (ValueError, TypeError) as error:
            raise SyncError(ErrorCode.RESPONSE, "Resposta JSON Google invalida") from error
        if not isinstance(payload, dict):
            raise SyncError(ErrorCode.RESPONSE, "Formato da resposta Google invalido")
        return payload


def _is_quota_response(response: Any) -> bool:
    try:
        payload = response.json()
        errors = payload.get("error", {}).get("errors", [])
        return any(item.get("reason") in {"rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded"} for item in errors if isinstance(item, dict))
    except (AttributeError, TypeError, ValueError):
        return False


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            from datetime import UTC, datetime

            return max(0.0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None
