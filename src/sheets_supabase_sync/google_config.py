from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .environment import load_environment_values
from .errors import ErrorCode, SyncError
from .retries import RetryPolicy

SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
PLACEHOLDER_MARKERS = ("replace", "example", "placeholder", "change-me")


@dataclass(frozen=True)
class GoogleSheetsConfig:
    credential_file: Path
    spreadsheet_id: str
    sheet_name: str
    optional_range: str | None = None
    timeout_seconds: float = 15.0
    retry_policy: RetryPolicy = RetryPolicy()


def load_google_sheets_config(root: Path) -> GoogleSheetsConfig:
    values = load_environment_values(root)
    credential_value = values.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    spreadsheet_id = values.get("GOOGLE_TEST_SPREADSHEET_ID", "").strip()
    sheet_name = values.get("GOOGLE_TEST_SHEET_NAME", "").strip()
    if not credential_value or not spreadsheet_id or not sheet_name:
        raise SyncError(ErrorCode.CONFIGURATION, "Configuracao Google Sheets incompleta")
    if any(marker in spreadsheet_id.lower() for marker in PLACEHOLDER_MARKERS):
        raise SyncError(ErrorCode.CONFIGURATION, "Identificador da planilha ainda e placeholder")
    try:
        timeout_seconds = float(values.get("GOOGLE_HTTP_TIMEOUT_SECONDS", "15"))
        retry_policy = RetryPolicy(
            max_attempts=int(values.get("GOOGLE_RETRY_MAX_ATTEMPTS", "4")),
            base_delay_seconds=float(values.get("GOOGLE_RETRY_BASE_DELAY_SECONDS", "1")),
            max_delay_seconds=float(values.get("GOOGLE_RETRY_MAX_DELAY_SECONDS", "16")),
            max_elapsed_seconds=float(values.get("GOOGLE_RETRY_MAX_ELAPSED_SECONDS", "45")),
            jitter_ratio=float(values.get("GOOGLE_RETRY_JITTER_RATIO", "0.2")),
        )
    except ValueError as error:
        raise SyncError(ErrorCode.CONFIGURATION, "Valores de timeout ou retry invalidos") from error
    optional_range = values.get("GOOGLE_TEST_OPTIONAL_RANGE", "").strip() or None
    config = GoogleSheetsConfig(Path(credential_value).expanduser(), spreadsheet_id, sheet_name, optional_range, timeout_seconds, retry_policy)
    validate_google_sheets_config(config, root)
    return config


def validate_google_sheets_config(config: GoogleSheetsConfig, repository_root: Path) -> None:
    credential_file = config.credential_file.resolve()
    repository = repository_root.resolve()
    if not credential_file.is_file():
        raise SyncError(ErrorCode.CREDENTIAL_MISSING, "Arquivo de credencial Google ausente")
    if credential_file == repository or repository in credential_file.parents:
        raise SyncError(ErrorCode.CREDENTIAL_INVALID, "Credencial Google deve permanecer fora do repositorio")
    if not config.spreadsheet_id.strip() or not config.sheet_name.strip() or config.timeout_seconds <= 0:
        raise SyncError(ErrorCode.CONFIGURATION, "Configuracao Google Sheets invalida")
    try:
        payload = json.loads(credential_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SyncError(ErrorCode.CREDENTIAL_INVALID, "JSON de credencial Google invalido") from error
    if not isinstance(payload, dict) or payload.get("type") != "service_account":
        raise SyncError(ErrorCode.CREDENTIAL_INVALID, "Tipo de credencial Google invalido")
    if not payload.get("private_key") or not payload.get("client_email") or not payload.get("token_uri"):
        raise SyncError(ErrorCode.CREDENTIAL_INVALID, "Estrutura da credencial Google incompleta")
