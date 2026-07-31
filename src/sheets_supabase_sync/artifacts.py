from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import DiffResult

SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|service[_-]?role|password|secret|token)\s*[:=]\s*['\"]?[^\s'\"]+")


def scan_secrets(text: str) -> list[str]:
    return [match.group(1) for match in SECRET_PATTERN.finditer(text)]


def write_artifacts(directory: Path, manifest: dict[str, Any], report: str, sql: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=False, indent=2)
    findings = scan_secrets(payload + report + sql)
    if findings:
        raise ValueError(f"Possivel segredo nos artefatos: {', '.join(findings)}")
    (directory / "manifest.json").write_text(payload + "\n", encoding="utf-8")
    (directory / "report.md").write_text(report, encoding="utf-8")
    (directory / "sync.sql").write_text(sql, encoding="utf-8")


def markdown_report(diff: DiffResult) -> str:
    rows = [("Linhas novas", len(diff.new)), ("Linhas alteradas", len(diff.changed)), ("Linhas removidas", len(diff.removed)),
            ("Linhas restauradas", len(diff.restored)), ("Linhas duplicadas", len(diff.duplicates)), ("Novas colunas", len(diff.new_columns)),
            ("Colunas ausentes", len(diff.missing_columns)), ("Possiveis renomeacoes", len(diff.possible_renames)),
            ("Tipos incompativeis", len(diff.incompatible_types))]
    return "# Relatorio de sincronizacao\n\n| Item | Quantidade |\n| --- | ---: |\n" + "".join(f"| {name} | {count} |\n" for name, count in rows)
