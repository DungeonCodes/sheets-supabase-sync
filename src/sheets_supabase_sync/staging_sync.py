from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from .errors import ErrorCode, SyncError
from .google_sheets import SheetReadResult, validate_fictitious_fixture
from .raw_repository import RawStateRepository
from .raw_sync import RawInputRow, RawSyncSource
from .raw_sync_service import RawSynchronizationService, RawSyncResult
from .sources import DataSource


class StagingSyncMode(StrEnum):
    DRY_RUN = "dry-run"
    APPLY_STAGING = "apply-staging"


class GoogleSheetReader(Protocol):
    def read(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        optional_range: str | None = None,
    ) -> SheetReadResult: ...


class StagingSyncOrchestrator:
    """Compoe leitura Google e core raw sem manter rede externa na transacao."""

    def __init__(self, reader: GoogleSheetReader, repository: RawStateRepository) -> None:
        self._reader = reader
        self._repository = repository

    def run(
        self,
        source: DataSource,
        mode: StagingSyncMode,
        optional_range: str | None = None,
    ) -> RawSyncResult:
        if not source.enabled:
            raise SyncError(ErrorCode.SOURCE_INACTIVE, "Fonte configurada nao esta ativa")
        sheet = self._reader.read(source.spreadsheet_id, source.sheet_name, optional_range)
        validate_fictitious_fixture(sheet)
        raw_source = RawSyncSource(
            logical_name=source.name,
            source_hash=sheet.source_hash,
            spreadsheet_id=source.spreadsheet_id,
            sheet_name=source.sheet_name,
            target_table=source.target_table,
            business_key=source.business_key,
        )
        rows = tuple(
            RawInputRow(row.source_row_number, dict(zip(sheet.normalized_header, row.values, strict=True)))
            for row in sheet.rows
        )
        service = RawSynchronizationService(self._repository)
        if mode is StagingSyncMode.DRY_RUN:
            previous = self._repository.preview_snapshot(raw_source, sheet.normalized_header, sheet.read_at)
            return service.dry_run(
                raw_source,
                sheet.normalized_header,
                rows,
                sheet.read_at,
                previous=previous,
                duration_ms=sheet.duration_ms,
            )
        if mode is StagingSyncMode.APPLY_STAGING:
            return service.persist(
                raw_source,
                sheet.normalized_header,
                rows,
                sheet.read_at,
                duration_ms=sheet.duration_ms,
            )
        raise SyncError(ErrorCode.CONFIGURATION, "Modo de sincronizacao remota invalido")
