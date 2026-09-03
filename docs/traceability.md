# Matriz de rastreabilidade

A rastreabilidade oficial e detalhada da Atividade 3 está em [activity-3/requirements-traceability.md](activity-3/requirements-traceability.md). Ela é a referência para status, evidência, lacuna, aceite, prioridade, dependência e risco.

Estado atual: o pipeline raw e o schema drift completo foram validados no staging com fixture fictícia. Retry operacional, observabilidade e política de retenção foram validados em seus alcances documentados; a migration 4 de retenção foi aplicada e validada por catálogo no staging. Os parágrafos cronológicos abaixo preservam evidência anterior e não substituem este estado.

## Capacidades técnicas existentes

Esta tabela é apenas um índice de evidências; não substitui os 40 requisitos oficiais.

| Capacidade | Código/DDL | Teste/evidência | Status auditado |
| --- | --- | --- | --- |
| Projeto por instituição | `sources.py`; baseline | `test_isolated_institution.py`, ADR 20260803 | `validated` |
| Fontes isoladas e execução independente | `sources.py`, `batch.py`, `orchestration.py`, repositorio raw | duas fixtures com schemas distintos; current/history/runs, drift, lock, falha, retry e lifecycle isolados no PostgreSQL local; resumo agregado | `multi_source_local_validated` |
| Identificadores seguros | `identifiers.py`, `sql_generator.py` | unit/security | `validated` |
| Contratos e schema drift offline | `contracts.py`, `diff.py` | contract/unit | `validated` |
| Snapshots, diff, tombstones e SQL | `snapshot.py`, `diff.py`, `sql_generator.py` | `test_sync.py` | `validated` |
| Logs/health e alertas | `operational_events.py`, `alerting.py`, `observability.py`, `health.py` | unit: severidade, sanitização, política, deduplicação e SMTP mockado | `validated_offline` |
| Retenção, minimização e LGPD | migration 4, `retention.md`, ADR 20260825 e testes local/offline | 4/4 local/remoto; catálogo staging confirmou lifecycle/backfill, funções, triggers, RLS, grants, índices e raw preservado; nenhum purge ou sync | `retention_schema_staging_applied_validated` |
| Retry operacional seguro | `operational_failures.py`, `postgres_retry.py`, `raw_sync_service.py`, `raw_repository.py` | PostgreSQL local: lock, busy, rollback, retry, idempotência e commit ambíguo; staging read-only: pooler, psycopg, migrations, lint e estado agregado | `validated_remote_read_only` |
| Histórico da baseline | migration `20260804000000` | `migration list`: duas versões locais, uma remota, sem divergência | `validated` |
| Estado raw atual por fonte/chave | migration `20260806120000` aplicada no staging; `raw_state.py`, `raw_repository.py` | PostgreSQL local e catálogo remoto: DDL, constraints, grants, RLS, transações e advisory lock; tabelas vazias | `validated` |
| Cinco tabelas operacionais | migration `20260804000000` | catálogo remoto: cinco tabelas, 27 constraints, 14 índices e zero linhas | `validated` |
| RLS/revokes operacionais | migration `20260804000000` | catálogo: RLS nas cinco, zero policies, `anon`/`authenticated` sem acesso e backend com grants esperados | `validated` |
| Data API da fundação | configuração segura | verificação somente de leitura: HTTP 200 | `validated` |
| Google Sheets real | leitor HTTP v4 read-only e Service Account implementados | 29 testes offline; diagnóstico e opt-in reais: 7 colunas/5 linhas fictícias | `partially_validated` |
| Raw persistido pelo pipeline | `RawSynchronizationService` + `PostgresRawRepository` | staging: duas sincronizações da fixture fictícia; 5 estados, 5 inserts e repetição sem novo evento | `validated` |
| Contrato analitico minimo | ADR 20260903 | caso, grain, Star, fato, dimensoes, metricas, minimizacao, acesso futuro e BI MVP definidos; sem objetos | `planned` |

O gate de 2026-08-11 definiu `raw_import_rows` como event-only. Naquele ponto, a persistência integrada ainda era `requires_changes`; os checkpoints posteriores de 2026-08-13 e 2026-08-17 a validaram no alcance controlado descrito abaixo. A decisão está em `decisions/20260811_raw_import_event_only_semantics.md`.

Follow-up local: terceira migration, adaptador `psycopg`, event-only, rollback e concorrência foram
validados em PostgreSQL real. O gate agora está `approved_for_staging`; o staging continua com as
duas migrations anteriores e sem sincronização.

Follow-up de deploy: a terceira migration foi aplicada e o catálogo remoto passou a estar validado para
event-only. Naquela data, a persistência integrada ainda estava planejada e o staging permanecia vazio.

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

Checkpoint de mudanças de 2026-08-17: update, tombstone, restore e reorder da
fixture fictícia foram validados um por vez no staging. A identidade lógica foi
preservada em todos os cenários; o reorder não gerou evento nem versão nova.
O pipeline raw persistido permanece `validated` para esse ciclo controlado.

Checkpoint completo de schema drift: a política integrada bloqueou adição,
remoção e rename de header antes de qualquer mutação raw e registrou requests
operacionais pendentes. Reorder foi compatível por mapeamento por nome, sem
evento ou versão nova; header duplicado foi rejeitado pelo leitor antes da
transação. A baseline restaurada permanece equivalente.
| Schema analitico/BI | contrato definido; objetos inexistentes | ADR 20260903; nenhuma evidencia executavel ainda | `planned` |
| E-mail e scheduler implantado | regras/configuração parciais | nenhum transporte/provider | `planned` |

Consulte também [análise de lacunas](activity-3/gap-analysis.md), [plano](activity-3/implementation-plan.md), [riscos](activity-3/risk-register.md), [decisões](activity-3/open-decisions.md) e [gates](activity-3/validation-checkpoints.md).

## Checkpoint de desenho de retenção em 2026-08-25

As três migrations aplicadas foram auditadas offline. A futura evolução mínima
ficou limitada a lifecycle em `data_sources`, `retention_holds`, `purge_runs` e
índices de seleção. Prazos continuam externos e versionados; current não entra
em purge histórico; `last_sync_run_id` permanece restritiva e runs
ambíguas/não terminais são protegidas. Não houve migration, DDL, purge ou
acesso externo. Classificação: `retention_schema_design_validated`.
