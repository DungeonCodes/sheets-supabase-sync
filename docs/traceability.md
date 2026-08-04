# Matriz de rastreabilidade

| Requisito ou decisão | Código | Teste | Migration | Documento | Status |
| --- | --- | --- | --- | --- | --- |
| Projeto por instituição | `sources.py` | `test_isolated_institution.py` | `20260803000000` | ADR 20260803 | validated_offline |
| Fontes/tabelas espelho isoladas | `mirror_schema.py` | `test_isolated_institution.py` | sob demanda | architecture | validated_offline |
| Identificadores seguros | `identifiers.py` | unit/security | — | security | validated_offline |
| Contratos | `contracts.py` | contract | — | testing | validated_offline |
| Snapshots, diff e SQL | `snapshot.py`, `diff.py`, `sql_generator.py` | `test_sync.py` | — | workflow | validated_offline |
| Exclusão/restauração | `diff.py` | `test_sync.py` | — | workflow | validated_offline |
| Doctor, alertas e logs | `doctor.py`, `health.py`, `observability.py` | unit | `20260803001000` | monitoring | validated_offline |
| Rollback/advisory lock/concorrência | `executors.py` | integration/end_to_end | `20260803001000` | runbook | prepared_not_executed |
| Google Sheets real | `source_reader.py` fake | unit | — | roadmap | planned |
| Supabase local | `executors.py` | integration | migrations | testing | blocked |
| Supabase remoto | — | — | — | security | out_of_scope |
| Scheduler produção | `scheduling.py` | isolated | — | roadmap | planned |
| CI offline e segredos | `.github/workflows/ci.yml` | security | — | testing | validated_offline |
