from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Environment:
    app_env: str
    project_ref: str
    allowed_ref: str
    supabase_url: str
    db_url: str
    secret_key: str
    google_file: str


def load_environment_values(root: Path) -> dict[str, str]:
    path = root / ".env.local"
    if not path.is_file():
        raise ValueError("Configuracao local ausente")
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Linha invalida: {line_number}")
        key, value = line.split("=", 1)
        if not key.isidentifier() or key in values:
            raise ValueError(f"Chave invalida ou duplicada: {line_number}")
        values[key] = os.environ.get(key, value)
    return values


def load_environment(root: Path) -> Environment:
    values = load_environment_values(root)
    environment = Environment(
        values.get("APP_ENV", ""),
        values.get("SUPABASE_PROJECT_REF", ""),
        values.get("SUPABASE_ALLOWED_PROJECT_REF", ""),
        values.get("SUPABASE_URL", ""),
        values.get("SUPABASE_DB_URL", ""),
        values.get("SUPABASE_SECRET_KEY", values.get("SUPABASE_SERVICE_ROLE_KEY", "")),
        values.get("GOOGLE_SERVICE_ACCOUNT_FILE", ""),
    )
    if environment.app_env == "production":
        raise ValueError("Production bloqueada")
    return environment


def validate_environment(environment: Environment) -> None:
    if environment.app_env != "staging" or not environment.project_ref or environment.project_ref != environment.allowed_ref:
        raise ValueError("Project ref nao autorizado")
    supabase_url = urlparse(environment.supabase_url)
    database_url = urlparse(environment.db_url)
    if supabase_url.scheme != "https" or supabase_url.hostname != f"{environment.project_ref}.supabase.co":
        raise ValueError("URL Supabase incompativel")
    if database_url.scheme not in {"postgres", "postgresql"} or database_url.path.strip("/") != "postgres":
        raise ValueError("URL PostgreSQL invalida")


def sanitize(text: str) -> str:
    return "Falha de configuracao ou conectividade; detalhe sensivel ocultado"
