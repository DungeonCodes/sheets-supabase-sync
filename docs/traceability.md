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
| Estado raw atual por fonte/chave | migration `20260806120000` aplicada no staging; `raw_state.py`, `raw_repository.py` | PostgreSQL local e catálogo remoto: DDL, constraints, grants, RLS, transações e advisory lock; tabelas vazias | `validated` |
| Cinco tabelas operacionais | migration `20260804000000` | catálogo remoto: cinco tabelas, 27 constraints, 14 índices e zero linhas | `validated` |
| RLS/revokes operacionais | migration `20260804000000` | catálogo: RLS nas cinco, zero policies, `anon`/`authenticated` sem acesso e backend com grants esperados | `validated` |
| Data API da fundação | configuração segura | verificação somente de leitura: HTTP 200 | `validated` |
| Google Sheets real | leitor HTTP v4 read-only e Service Account implementados | 29 testes offline; diagnóstico e opt-in reais: 7 colunas/5 linhas fictícias | `partially_validated` |
| Raw persistido pelo pipeline | `RawSynchronizationService` + `PostgresRawRepository` | staging: duas sincronizações da fixture fictícia; 5 estados, 5 inserts e repetição sem novo evento | `validated` |

O gate de 2026-08-11 definiu `raw_import_rows` como event-only. A persistência integrada continua
`requires_changes`: o schema atual não representa tombstone sem ambiguidade e o adaptador
PostgreSQL transacional ainda não existe. A decisão está em `decisions/20260811_raw_import_event_only_semantics.md`.

Follow-up local: terceira migration, adaptador `psycopg`, event-only, rollback e concorrência foram
validados em PostgreSQL real. O gate agora está `approved_for_staging`; o staging continua com as
duas migrations anteriores e sem sincronização.

Follow-up de deploy: a terceira migration foi aplicada e o catálogo remoto agora está validado para
event-only. A persistência integrada continua planejada; o staging permanece vazio.

Follow-up de integração em 2026-08-11: a fixture fictícia foi lida em modo
readonly e seu dry-run aprovou 5 inserções planejadas. A persistência integrada
permanece bloqueada por conectividade PostgreSQL direta ao staging; a falha
ocorreu antes da transação e o staging continua vazio.

Checkpoint integrado de 2026-08-13: com conectividade pelo Session Pooler
validada, a primeira sincronização da fixture fictícia persistiu 5 estados e
5 eventos insert em uma transação protegida por advisory lock. A segunda leitura
independente e sincronização gerou 5 `unchanged` e zero eventos novos. O staging
agora possui uma fonte e duas execuções aplicadas; versões permanecem em 1,
`import_errors=0`, migrations 3/3, RLS habilitado e zero policies.
| Staging/Star Schema/BI | inexistente | nenhuma evidência | `planned` |
| E-mail e scheduler implantado | regras/configuração parciais | nenhum transporte/provider | `planned` |

Consulte também [análise de lacunas](activity-3/gap-analysis.md), [plano](activity-3/implementation-plan.md), [riscos](activity-3/risk-register.md), [decisões](activity-3/open-decisions.md) e [gates](activity-3/validation-checkpoints.md).
