from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class SourceReader(Protocol):
    def read(self, spreadsheet_id: str, sheet_name: str) -> list[dict[str, Any]]: ...


class FakeSourceReader:
    def __init__(self, sheets: dict[tuple[str, str], Sequence[dict[str, Any]]]) -> None:
        self._sheets = sheets

    def read(self, spreadsheet_id: str, sheet_name: str) -> list[dict[str, Any]]:
        try:
            return [dict(row) for row in self._sheets[(spreadsheet_id, sheet_name)]]
        except KeyError as error:
            from .errors import ErrorCode, SyncError
            raise SyncError(ErrorCode.NOT_FOUND, "Planilha ou aba nao encontrada") from error
