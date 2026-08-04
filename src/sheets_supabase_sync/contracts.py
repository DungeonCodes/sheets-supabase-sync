from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .identifiers import normalize_headers
from .normalization import infer_type


class ContractStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True)
class SourceContract:
    sheet_name: str
    header_row: int
    required_columns: tuple[str, ...]
    business_key: tuple[str, ...]
    expected_types: dict[str, str]
    max_empty_ratio: float = 1.0
    min_rows: int = 0
    max_rows: int | None = None
    allow_new_columns: bool = True


@dataclass(frozen=True)
class ContractResult:
    status: ContractStatus
    messages: tuple[str, ...]
    rows_read: int


def validate_contract(contract: SourceContract, sheet_name: str | None, rows: list[dict[str, Any]], previous_headers: tuple[str, ...] = ()) -> ContractResult:
    if sheet_name != contract.sheet_name:
        return ContractResult(ContractStatus.FAILED, ("Aba esperada nao encontrada",), len(rows))
    if not rows:
        return ContractResult(ContractStatus.FAILED, ("Planilha vazia",), 0)
    headers = tuple(normalize_headers(list(rows[0])))
    missing = set(contract.required_columns) - set(headers)
    if missing:
        return ContractResult(ContractStatus.BLOCKED, (f"Colunas obrigatorias ausentes: {', '.join(sorted(missing))}",), len(rows))
    if any(not row.get(key) for row in rows for key in contract.business_key):
        return ContractResult(ContractStatus.BLOCKED, ("Chave de negocio ausente ou vazia",), len(rows))
    removed = set(previous_headers) - set(headers)
    if removed:
        return ContractResult(ContractStatus.BLOCKED, (f"Colunas removidas: {', '.join(sorted(removed))}",), len(rows))
    new = set(headers) - set(previous_headers)
    if previous_headers and new and not contract.allow_new_columns:
        return ContractResult(ContractStatus.BLOCKED, ("Novas colunas nao permitidas",), len(rows))
    if len(rows) < contract.min_rows or contract.max_rows is not None and len(rows) > contract.max_rows:
        return ContractResult(ContractStatus.WARNING, ("Quantidade de linhas fora do limite esperado",), len(rows))
    for column, expected in contract.expected_types.items():
        if column in headers and infer_type([row.get(column) for row in rows]) != expected:
            return ContractResult(ContractStatus.BLOCKED, (f"Tipo inesperado em {column}",), len(rows))
    return ContractResult(ContractStatus.PASSED, (), len(rows))
