from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ExecutionResult:
    returncode: int
    stdout: str


Runner = Callable[..., subprocess.CompletedProcess[str]]


def assert_local_url(url: str, allowed_hosts: set[str] | None = None) -> None:
    host = urlparse(url).hostname
    permitted = {"127.0.0.1", "localhost", "::1"}
    if allowed_hosts:
        permitted.update(allowed_hosts)
    if host not in permitted:
        raise ValueError("Aplicacao recusada: somente host Supabase local e permitido.")


def apply_sql_locally(
    sql: str,
    database_url: str,
    allowed_hosts: set[str] | None = None,
    runner: Runner = subprocess.run,
) -> ExecutionResult:
    """Executa SQL somente contra PostgreSQL local, em transacao unica e sem logar a URL."""
    assert_local_url(database_url, allowed_hosts)
    command: Sequence[str] = ("psql", database_url, "--no-psqlrc", "--set", "ON_ERROR_STOP=1", "--single-transaction", "--quiet")
    try:
        completed = runner(command, input=_without_outer_transaction(sql), text=True, capture_output=True, check=False)
    except FileNotFoundError as error:
        raise RuntimeError("psql indisponivel; instale o cliente PostgreSQL apenas para aplicar no Supabase local.") from error
    if completed.returncode != 0:
        raise RuntimeError("Aplicacao local falhou; a transacao foi revertida.")
    return ExecutionResult(completed.returncode, completed.stdout)


def _without_outer_transaction(sql: str) -> str:
    lines = [line for line in sql.splitlines() if line.strip() not in {"BEGIN;", "COMMIT;"}]
    return "\n".join(lines) + "\n"
