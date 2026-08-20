# Roadmap

O [documento oficial da Atividade 3](decisions/20260806_inicie_etl_clientes_orientacao.md) ampliou o projeto. A sequência detalhada, os gates e os aceites estão no [plano de implementação](activity-3/implementation-plan.md).

## Estado atual

- Núcleo Python offline: snapshots, diff, contratos, schema drift, SQL auditável, isolamento por fonte, health, logs seguros e testes; leitor Google read-only implementado com transporte HTTP isolado.
- Baseline institucional: aplicada no staging em 2026-08-05 e reconciliada em 2026-08-06 por histórico, catálogo e Data API somente de leitura; cinco tabelas vazias, 27 constraints, 14 índices, RLS/grants coerentes e nenhuma policy.
- Migration incremental de estado raw: criada em 2026-08-06, aditiva, coberta por testes estruturais e comportamentais offline, validada em PostgreSQL local e aplicada ao staging em 2026-08-11; catálogo, grants mínimos e tabelas vazias foram confirmados somente por leitura.
- Raw integrado: validado no staging exclusivamente com a fixture fictícia; primeira carga, idempotência, update, tombstone, restore, reorder de linhas e schema drift completo preservaram identidade/estado. Permanecem ausentes: Star Schema, BI, RLS/RBAC hierárquico, e-mail, estudo completo de custos/free tiers, onboarding e Draw.io.

## Fases oficiais de execução

0. Fundação e banco.
1. Ingestão Google Sheets.
2. Raw e sincronização.
3. Qualidade e schema drift.
4. Modelagem analítica.
5. BI e segurança hierárquica.
6. Observabilidade e alertas.
7. Viabilidade e operação.
8. Fluxograma e apresentação.

## Próximo passo

O ciclo controlado de update, tombstone, restore, reorder e schema drift foi
validado no staging com a fixture fictícia. O próximo gate é falha/retry
operacional controlado, mediante autorização humana específica.
Decisões empresariais continuam em [open-decisions.md](activity-3/open-decisions.md); quase tempo
real, BI ou ferramenta adicional não devem ser presumidos.

## Checkpoint operacional de 2026-08-19

A política de retry e commit ambíguo passou por fault injection offline. `sync_runs.id` pode ser
gerado pelo cliente e reutilizado, portanto nenhuma migration nova foi criada. O gate segue aberto:
o teste PostgreSQL real de lock/rollback não executou por erro 500 do Docker Desktop. Próximo gate
único: recuperar o Supabase local e executar os testes `psycopg` opt-in.
