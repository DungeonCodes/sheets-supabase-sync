from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .config import load_config
from .doctor import doctor_exit_code, run_doctor
from .synchronizer import synchronize


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "doctor":
        _doctor(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description="Sincronizador local auditavel (dry-run por padrao).")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, default=Path("runtime/snapshots/latest.json"))
    parser.add_argument("--artifacts", type=Path, default=Path("runtime/artifacts/latest"))
    parser.add_argument("--mode", choices=("dry-run", "generate-sql", "apply-local"), default="dry-run")
    parser.add_argument("--database-url", help="URL PostgreSQL local; exigida somente em apply-local.")
    parser.add_argument("--allow-host", action="append", default=[], help="Host adicional explicitamente permitido para desenvolvimento.")
    args = parser.parse_args()
    with args.input.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    print(json.dumps(synchronize(rows, load_config(args.config), args.snapshot, args.artifacts, args.mode, args.database_url, set(args.allow_host)), ensure_ascii=False, indent=2))


def _doctor(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Diagnostico local seguro.")
    parser.add_argument("--config", type=Path, default=Path("configs/examples/institution.example.json"))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(arguments)
    checks = run_doctor(args.config, Path("runtime"), Path("supabase/migrations"))
    if args.format == "json":
        print(json.dumps([{"status": check.status.name.lower(), "message": check.message} for check in checks], ensure_ascii=False))
    else:
        labels = {0: "OK", 1: "AVISO", 2: "FALHA"}
        for check in checks:
            print(f"[{labels[int(check.status)]}] {check.message}")
    raise SystemExit(doctor_exit_code(checks))


if __name__ == "__main__":
    main()
