# Status executivo — Sheets → Supabase

## Objetivo e problema

O projeto substitui rotinas manuais em planilhas por uma ingestão rastreável, idempotente e preparada para evolução analítica. O pipeline preserva o último estado válido, registra mudanças e bloqueia publicações incorretas por falha ou schema drift.

## Situação atual

O pipeline operacional já foi validado, inclusive com múltiplas fontes, resiliência, controle de mudanças e governança. A etapa atual do projeto é a materialização da camada analítica e, posteriormente, sua exposição ao BI.

O fluxo validado lê Google Sheets em modo read-only, normaliza e valida o schema, calcula diferenças por identidade lógica e persiste current state e event history em PostgreSQL/Supabase. Transação, retry/rollback, advisory lock, reconciliação de commit ambíguo, observabilidade e alert policy fazem parte da trilha validada.

## Evidências principais

- 218 testes totais: 214 aprovados, 4 pulados e 0 falhas no gate multi-source local.
- 25 testes PostgreSQL multi-source aprovados.
- 4/4 migrations alinhadas no staging após a Migration 4 de retention/lifecycle.
- Prova multi-source com duas fontes fictícias, schemas diferentes e isolamento de dados, falhas e locks.
- Baseline operacional preservada: 1 `data_source`, 6 `sync_runs`, 8 `raw_import_rows`, 5 `raw_current_rows`, 0 `import_errors` e 3 `schema_change_requests`.
- Eventos: 5 inserts, 1 update, 1 tombstone e 1 restore; 0 tombstones ativos.
- Retention administrativo na validação: 0 `retention_holds` e 0 `purge_runs`.

## Status por área

| Área | Estado | Observação |
| --- | --- | --- |
| Pipeline operacional | Validado | Raw, resiliência, controle de mudanças e governança |
| Retention/lifecycle | Aplicado e validado em staging | Schema estrutural concluído; executor real de purge é futuro |
| Multi-source | Validado localmente | Não equivale a operação produtiva ou scheduler persistente |
| Analytical contract | Definido | `DIM_SOURCE`, `DIM_CATEGORY`, `FACT_CATEGORY_SCORE` |
| Analytical schema | Em implementação | Temporariamente bloqueado pelo ambiente local |
| Transformação, RBAC e BI real | Planejado | Dependem da materialização analítica |
| Scheduler/runtime | Planejado | Cadência operacional ainda futura |
| E2E final | Pendente | Etapa de fechamento |

## Limitações e próximos passos

Permanecem para depois da reunião: Star Schema físico, transformação analítica, RBAC analítico, BI real, scheduler/runtime, E2E final, executor real de purge e operação produtiva. A decisão jurídica final, o canal administrativo e o transporte real de alertas também continuam futuros; isso não invalida os controles estruturais já validados.

Após a reunião, recuperar o ambiente local e retomar o schema analítico com revisão humana antes de qualquer aplicação de migration.

