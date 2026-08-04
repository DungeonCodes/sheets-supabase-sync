from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .health import HealthStatus


@dataclass(frozen=True)
class DoctorCheck:
    status: HealthStatus
    message: str


def run_doctor(config_path: Path, runtime_dir: Path, migrations_dir: Path) -> tuple[DoctorCheck, ...]:
    checks = [_check_config(config_path), _check_runtime(runtime_dir), _check_migrations(migrations_dir), _check_credentials()]
    return tuple(checks)


def doctor_exit_code(checks: tuple[DoctorCheck, ...]) -> int:
    return max((int(check.status) for check in checks), default=0)


def _check_config(path: Path) -> DoctorCheck:
    return DoctorCheck(HealthStatus.OK, "Configuracao valida") if path.exists() else DoctorCheck(HealthStatus.FAILURE, "Configuracao ausente")


def _check_runtime(path: Path) -> DoctorCheck:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".doctor-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return DoctorCheck(HealthStatus.OK, "Runtime gravavel")
    except OSError:
        return DoctorCheck(HealthStatus.FAILURE, "Runtime nao gravavel")


def _check_migrations(path: Path) -> DoctorCheck:
    return DoctorCheck(HealthStatus.OK, "Migrations conhecidas") if list(path.glob("*.sql")) else DoctorCheck(HealthStatus.FAILURE, "Nenhuma migration encontrada")


def _check_credentials() -> DoctorCheck:
    if os.getenv("DATABASE_URL"):
        return DoctorCheck(HealthStatus.OK, "Credencial de banco presente")
    return DoctorCheck(HealthStatus.WARNING, "Credencial de banco ausente; aplicacao local indisponivel")
