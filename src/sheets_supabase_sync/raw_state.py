from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from .errors import ErrorCode, SyncError
from .raw_sync import RawChangePlan, RawRecord


class RawStateOperation(StrEnum):
    INSERT = "insert"
    UPDATE = "update"
    TOMBSTONE = "tombstone"
    RESTORE = "restore"
    TOUCH = "touch"


@dataclass(frozen=True)
class RawCurrentRow:
    """Espelha uma linha de `public.raw_current_rows`: identidade por fonte e chave."""

    key_hash: str
    content_hash: str
    source_row_number: int | None
    is_deleted: bool = False
    version: int = 1


@dataclass(frozen=True)
class RawStateCommand:
    operation: RawStateOperation
    record: RawRecord


def plan_state_commands(plan: RawChangePlan) -> tuple[RawStateCommand, ...]:
    groups = (
        (RawStateOperation.INSERT, plan.new),
        (RawStateOperation.UPDATE, plan.changed),
        (RawStateOperation.RESTORE, plan.restored),
        (RawStateOperation.TOMBSTONE, plan.removed),
        (RawStateOperation.TOUCH, plan.unchanged),
    )
    return tuple(RawStateCommand(operation, record) for operation, records in groups for record in records)


def history_change_type(operation: RawStateOperation) -> str | None:
    """Classificacao anexada ao historico; exclusao nao e observada na planilha."""
    return {
        RawStateOperation.INSERT: "inserted",
        RawStateOperation.UPDATE: "changed",
        RawStateOperation.RESTORE: "restored",
        RawStateOperation.TOUCH: "unchanged",
    }.get(operation)


def apply_state_command(current: RawCurrentRow | None, command: RawStateCommand) -> RawCurrentRow:
    return _HANDLERS[command.operation](current, command.record)


def _insert(current: RawCurrentRow | None, record: RawRecord) -> RawCurrentRow:
    if current is not None:
        raise SyncError(ErrorCode.VALIDATION, "Estado atual ja existe para a chave")
    return RawCurrentRow(record.key_hash, record.content_hash, record.source_row_number)


def _update(current: RawCurrentRow | None, record: RawRecord) -> RawCurrentRow:
    active = _require_active(current)
    return replace(
        active,
        content_hash=record.content_hash,
        source_row_number=record.source_row_number,
        version=active.version + 1,
    )


def _tombstone(current: RawCurrentRow | None, record: RawRecord) -> RawCurrentRow:
    active = _require_active(current)
    return replace(active, is_deleted=True, version=active.version + 1)


def _restore(current: RawCurrentRow | None, record: RawRecord) -> RawCurrentRow:
    if current is None or not current.is_deleted:
        raise SyncError(ErrorCode.VALIDATION, "Restauracao exige estado atual excluido")
    return replace(
        current,
        content_hash=record.content_hash,
        source_row_number=record.source_row_number,
        is_deleted=False,
        version=current.version + 1,
    )


def _touch(current: RawCurrentRow | None, record: RawRecord) -> RawCurrentRow:
    active = _require_active(current)
    if active.content_hash != record.content_hash:
        raise SyncError(ErrorCode.VALIDATION, "Linha inalterada nao pode mudar o conteudo")
    return replace(active, source_row_number=record.source_row_number)


def _require_active(current: RawCurrentRow | None) -> RawCurrentRow:
    if current is None or current.is_deleted:
        raise SyncError(ErrorCode.VALIDATION, "Operacao exige estado atual ativo")
    return current


_HANDLERS = {
    RawStateOperation.INSERT: _insert,
    RawStateOperation.UPDATE: _update,
    RawStateOperation.TOMBSTONE: _tombstone,
    RawStateOperation.RESTORE: _restore,
    RawStateOperation.TOUCH: _touch,
}
