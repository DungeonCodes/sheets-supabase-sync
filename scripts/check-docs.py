from pathlib import Path
import re
import sys

root = Path(__file__).parents[1]
required = ["docs/index.md", "docs/traceability.md", ".agents/skills/maintainable-python/SKILL.md", ".github/workflows/ci.yml"]
errors = [f"ausente: {path}" for path in required if not (root / path).exists()]
for path in (root / "docs").glob("*.md"):
    text = path.read_text(encoding="utf-8")
    if re.search(r"C:\\Users\\|sheets-supabase-sync\.agents|sheets-supabase-sync\.github", text): errors.append(f"caminho local: {path}")
    if path.name not in {"traceability.md"} and ("organization_id" in text or "tenant_id" in text): errors.append(f"termo obsoleto sem contexto: {path}")
print("OK" if not errors else "\n".join(errors))
sys.exit(bool(errors))
