# Matriz de rastreabilidade

A rastreabilidade oficial e detalhada da Atividade 3 está em [activity-3/requirements-traceability.md](activity-3/requirements-traceability.md). Ela é a referência para status, evidência, lacuna, aceite, prioridade, dependência e risco.

## Capacidades técnicas existentes

Esta tabela é apenas um índice de evidências; não substitui os 40 requisitos oficiais.

| Capacidade | Código/DDL | Teste/evidência | Status auditado |
| --- | --- | --- | --- |
| Projeto por instituição | `sources.py`; baseline | `test_isolated_institution.py`, ADR 20260803 | `validated` |
| Fontes isoladas e execução independente | `batch.py`, `orchestration.py` | teste de continuidade após falha | `validated` |
| Identificadores seguros | `identifiers.py`, `sql_generator.py` | unit/security | `validated` |
| Contratos e schema drift offline | `contracts.py`, `diff.py` | contract/unit | `validated` |
| Snapshots, diff, tombstones e SQL | `snapshot.py`, `diff.py`, `sql_generator.py` | `test_sync.py` | `validated` |
| Logs/health locais | `observability.py`, `health.py` | unit | `partially_validated` |
| Histórico da baseline | migration `20260804000000` | `migration list`: duas versões locais, uma remota, sem divergência | `validated` |
| Estado raw atual por fonte/chave | migration `20260806120000` (não aplicada); `raw_state.py`, `raw_repository.py` | `test_migration_raw_state.py`, `test_raw_state.py`; `lint` e `push --dry-run` aprovados | `implemented_not_validated` |
| Cinco tabelas operacionais | migration `20260804000000` | catálogo remoto: cinco tabelas, 27 constraints, 14 índices e zero linhas | `validated` |
| RLS/revokes operacionais | migration `20260804000000` | catálogo: RLS nas cinco, zero policies, `anon`/`authenticated` sem acesso e backend com grants esperados | `validated` |
| Data API da fundação | configuração segura | verificação somente de leitura: HTTP 200 | `validated` |
| Google Sheets real | leitor HTTP v4 read-only e Service Account implementados | 29 testes offline; diagnóstico e opt-in reais: 7 colunas/5 linhas fictícias | `partially_validated` |
| Raw persistido pelo pipeline | DDL de histórico e de estado existem; escrita integrada não | nenhum E2E; migration não aplicada | `planned` |
| Staging/Star Schema/BI | inexistente | nenhuma evidência | `planned` |
| E-mail e scheduler implantado | regras/configuração parciais | nenhum transporte/provider | `planned` |

Consulte também [análise de lacunas](activity-3/gap-analysis.md), [plano](activity-3/implementation-plan.md), [riscos](activity-3/risk-register.md), [decisões](activity-3/open-decisions.md) e [gates](activity-3/validation-checkpoints.md).
