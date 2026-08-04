from __future__ import annotations

import re

MAX_IDENTIFIER_LENGTH = 63
RESERVED_WORDS = frozenset({"all", "alter", "and", "as", "create", "delete", "drop", "from", "group", "insert", "join", "order", "select", "table", "update", "user", "where"})
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def normalize_identifier(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized or not normalized[0].isalpha():
        normalized = f"field_{normalized}".rstrip("_")
    return normalized[:MAX_IDENTIFIER_LENGTH]


def validate_identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value) or value in RESERVED_WORDS:
        raise ValueError("Identificador SQL invalido ou reservado")
    return value


def normalize_headers(headers: list[str]) -> list[str]:
    normalized = [normalize_identifier(header) for header in headers]
    duplicates = sorted({name for name in normalized if normalized.count(name) > 1})
    if duplicates:
        raise ValueError(f"Colisao de cabecalhos apos normalizacao: {', '.join(duplicates)}")
    return [validate_identifier(name) for name in normalized]
