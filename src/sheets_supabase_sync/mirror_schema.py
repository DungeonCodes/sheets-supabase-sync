from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .identifiers import normalize_headers, validate_identifier
from .normalization import infer_type


@dataclass(frozen=True)
class MirrorColumn:
    name: str
    sql_type: str


@dataclass(frozen=True)
class MirrorSchema:
    target_table: str
    columns: tuple[MirrorColumn, ...]


def propose_schema(target_table: str, rows: list[dict[str, Any]]) -> MirrorSchema:
    table = validate_identifier(target_table)
    headers = list(rows[0]) if rows else []
    normalized = normalize_headers(headers)
    columns = tuple(MirrorColumn(name, _to_sql_type(infer_type([row.get(header) for row in rows]))) for header, name in zip(headers, normalized, strict=True))
    return MirrorSchema(table, columns)


def create_table_sql(schema: MirrorSchema) -> str:
    fields = ["external_key text not null", "raw_data jsonb not null", "row_hash text not null", "deleted_at timestamptz", "created_at timestamptz not null default now()", "updated_at timestamptz not null default now()"]
    fields.extend(f"{column.name} {column.sql_type}" for column in schema.columns if column.name != "external_key")
    fields.append("unique (external_key)")
    return f"CREATE TABLE IF NOT EXISTS public.{schema.target_table} (\n  " + ",\n  ".join(fields) + "\n);\n"


def _to_sql_type(inferred: str) -> str:
    return {"boolean": "boolean", "integer": "bigint", "numeric": "numeric", "date": "date", "text": "text"}[inferred]
