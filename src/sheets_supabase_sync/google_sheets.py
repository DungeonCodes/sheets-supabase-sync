from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from time import monotonic

from .errors import ErrorCode, SyncError
from .hashing import deterministic_hash
from .identifiers import normalize_headers
from .observability import log_event
from .retries import RetryNotice, RetryPolicy, retry

_PROHIBITED_FIXTURE_HEADERS = frozenset({"cpf", "email", "e_mail", "telefone", "phone", "nome", "name"})
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_LONG_DIGIT_SEQUENCE = re.compile(r"(?:\D|^)(\d{10,14})(?:\D|$)")


class SheetsTransport(Protocol):
    def get_metadata(self, spreadsheet_id: str, timeout_seconds: float) -> dict[str, Any]: ...

    def get_values(self, spreadsheet_id: str, sheet_range: str, timeout_seconds: float) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SheetRow:
    source_row_number: int
    values: tuple[str, ...]


@dataclass(frozen=True)
class SheetReadResult:
    sheet_name: str
    sheet_count: int
    header: tuple[str, ...]
    normalized_header: tuple[str, ...]
    rows: tuple[SheetRow, ...]
    empty_rows_ignored: int
    read_at: datetime
    source_hash: str
    retry_count: int
    duration_ms: int


class GoogleSheetsReader:
    def __init__(
        self,
        transport: SheetsTransport,
        *,
        retry_policy: RetryPolicy = RetryPolicy(),
        timeout_seconds: float = 15.0,
        pause: Callable[[float], None] | None = None,
        random_value: Callable[[], float] | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        logger: logging.Logger | None = None,
        monotonic_clock: Callable[[], float] = monotonic,
    ) -> None:
        self._transport = transport
        self._retry_policy = retry_policy
        self._timeout_seconds = timeout_seconds
        self._pause = pause
        self._random_value = random_value
        self._clock = clock
        self._logger = logger or logging.getLogger(__name__)
        self._monotonic_clock = monotonic_clock
        self._retry_notices: list[RetryNotice] = []

    def read(self, spreadsheet_id: str, sheet_name: str, optional_range: str | None = None) -> SheetReadResult:
        started = self._monotonic_clock()
        self._retry_notices = []
        metadata = self._with_retry(lambda: self._transport.get_metadata(spreadsheet_id, self._timeout_seconds))
        sheets = self._sheet_titles(metadata)
        if sheet_name not in sheets:
            raise SyncError(ErrorCode.SHEET_NOT_FOUND, "Aba configurada nao encontrada")
        escaped_name = sheet_name.replace("'", "''")
        sheet_range = f"'{escaped_name}'"
        if optional_range:
            sheet_range = f"{sheet_range}!{optional_range}"
        response = self._with_retry(lambda: self._transport.get_values(spreadsheet_id, sheet_range, self._timeout_seconds))
        duration_ms = round((self._monotonic_clock() - started) * 1000)
        result = self._build_result(response, spreadsheet_id, sheet_name, len(sheets), duration_ms)
        log_event(
            self._logger,
            "google_sheet_read_succeeded",
            status="success",
            rows_read=len(result.rows),
            columns_read=len(result.header),
            empty_rows=result.empty_rows_ignored,
            retries=result.retry_count,
            data_source_id=result.source_hash[:12],
            duration_ms=result.duration_ms,
        )
        return result

    def _with_retry(self, operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"policy": self._retry_policy, "on_retry": self._on_retry}
        if self._pause is not None:
            kwargs["pause"] = self._pause
        if self._random_value is not None:
            kwargs["random_value"] = self._random_value
        return retry(operation, **kwargs)

    def _on_retry(self, notice: RetryNotice) -> None:
        self._retry_notices.append(notice)
        log_event(self._logger, "google_sheet_retry", attempt=notice.attempt, error_code=notice.error_code, wait_ms=round(notice.wait_seconds * 1000))

    @staticmethod
    def _sheet_titles(metadata: dict[str, Any]) -> tuple[str, ...]:
        if not isinstance(metadata, dict) or not isinstance(metadata.get("sheets"), list):
            raise SyncError(ErrorCode.RESPONSE, "Resposta de metadados Google invalida")
        titles: list[str] = []
        for item in metadata["sheets"]:
            properties = item.get("properties") if isinstance(item, dict) else None
            title = properties.get("title") if isinstance(properties, dict) else None
            if isinstance(title, str):
                titles.append(title)
        if not titles:
            raise SyncError(ErrorCode.RESPONSE, "Resposta de metadados sem abas")
        return tuple(titles)

    def _build_result(self, response: dict[str, Any], spreadsheet_id: str, sheet_name: str, sheet_count: int, duration_ms: int) -> SheetReadResult:
        values = response.get("values") if isinstance(response, dict) else None
        if not isinstance(values, list) or not values:
            raise SyncError(ErrorCode.EMPTY_SHEET, "Planilha vazia")
        raw_header = values[0]
        if not isinstance(raw_header, list) or not raw_header:
            raise SyncError(ErrorCode.EMPTY_SHEET, "Cabecalho ausente")
        header = tuple(str(value).strip() for value in raw_header)
        if any(not value for value in header):
            raise SyncError(ErrorCode.SCHEMA, "Cabecalho contem coluna vazia")
        if len(set(header)) != len(header):
            raise SyncError(ErrorCode.SCHEMA, "Cabecalho contem colunas duplicadas")
        try:
            normalized_header = tuple(normalize_headers(list(header)))
        except ValueError as error:
            raise SyncError(ErrorCode.SCHEMA, "Cabecalho invalido para identificadores futuros") from error
        rows: list[SheetRow] = []
        empty_rows = 0
        for source_row_number, raw_row in enumerate(values[1:], start=2):
            if not isinstance(raw_row, list):
                raise SyncError(ErrorCode.RESPONSE, "Linha da resposta Google invalida")
            row = ["" if value is None else str(value) for value in raw_row]
            if not any(value.strip() for value in row):
                empty_rows += 1
                continue
            if len(row) > len(header):
                raise SyncError(ErrorCode.SCHEMA, "Linha possui mais celulas que o cabecalho")
            row.extend([""] * (len(header) - len(row)))
            rows.append(SheetRow(source_row_number, tuple(row)))
        return SheetReadResult(
            sheet_name=sheet_name,
            sheet_count=sheet_count,
            header=header,
            normalized_header=normalized_header,
            rows=tuple(rows),
            empty_rows_ignored=empty_rows,
            read_at=self._clock(),
            source_hash=deterministic_hash({"spreadsheet_id": spreadsheet_id, "sheet_name": sheet_name}),
            retry_count=len(self._retry_notices),
            duration_ms=duration_ms,
        )


def validate_fictitious_fixture(result: SheetReadResult) -> None:
    if _PROHIBITED_FIXTURE_HEADERS.intersection(result.normalized_header):
        raise SyncError(ErrorCode.VALIDATION, "Fixture possui coluna de dado pessoal proibida")
    for row in result.rows:
        for value in row.values:
            if _EMAIL.search(value) or _LONG_DIGIT_SEQUENCE.search(value):
                raise SyncError(ErrorCode.VALIDATION, "Fixture possui padrao de dado pessoal proibido")
