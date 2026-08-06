from __future__ import annotations

import json

from .identifiers import validate_identifier
from .models import DiffResult, Record


def _literal(value: object) -> str:
    return "'" + json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).replace("'", "''") + "'::jsonb"


def generate_sql(diff: DiffResult, table_name: str, source_id: str) -> str:
    table = validate_identifier(table_name)
    source = source_id.replace("'", "''")
    statements = ["BEGIN;", "-- Revisar antes de executar. Nenhuma alteracao de schema e automatica."]
    for record in [*diff.new, *diff.changed, *diff.restored]:
        statements.append(_upsert(table, source, record))
    for record in diff.removed:
        key = record.key.replace("'", "''")
        statements.append(f"UPDATE {table} SET deleted_at = now(), updated_at = now() WHERE source_id = '{source}' AND external_key = '{key}';")
    for name in diff.new_columns:
        statements.append(f"-- PENDENCIA_SCHEMA: nova coluna {name}; nao aplicar ALTER TABLE automaticamente.")
    for name in diff.missing_columns:
        statements.append(f"-- PENDENCIA_SCHEMA: coluna ausente {name}; DROP COLUMN proibido automaticamente.")
    for old, new in diff.possible_renames:
        statements.append(f"-- PENDENCIA_SCHEMA: possivel renomeacao {old} -> {new}; revisao humana obrigatoria.")
    for name, old_type, new_type in diff.incompatible_types:
        statements.append(f"-- PENDENCIA_SCHEMA: tipo incompativel {name}: {old_type} -> {new_type}; alteracao destrutiva proibida.")
    statements.append("COMMIT;")
    return "\n".join(statements) + "\n"


def generate_schema_request_sql(diff: DiffResult, source_name: str) -> str:
    previous = {"missing_columns": diff.missing_columns, "possible_renames": diff.possible_renames, "incompatible_types": diff.incompatible_types}
    proposed = {"new_columns": diff.new_columns}
    escaped = source_name.replace("'", "''")
    return (
        "BEGIN;\n"
        "INSERT INTO public.schema_change_requests (data_source_id, change_type, previous_schema, proposed_schema) "
        "SELECT id, 'blocked_schema_change', " + _literal(previous) + ", " + _literal(proposed) +
        " FROM public.data_sources WHERE name = '" + escaped + "';\n"
        "COMMIT;\n"
    )


def _upsert(table: str, source: str, record: Record) -> str:
    key = record.key.replace("'", "''")
    return (f"INSERT INTO {table} (source_id, external_key, raw_data, row_hash, deleted_at) VALUES "
            f"('{source}', '{key}', {_literal(record.values)}, '{record.row_hash}', NULL) "
            "ON CONFLICT (source_id, external_key) DO UPDATE SET raw_data = EXCLUDED.raw_data, row_hash = EXCLUDED.row_hash, deleted_at = NULL, updated_at = now() "+
            "WHERE " + table + ".row_hash IS DISTINCT FROM EXCLUDED.row_hash OR " + table + ".deleted_at IS NOT NULL;")
