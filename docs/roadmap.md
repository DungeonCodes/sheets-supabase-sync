# Roadmap

O [documento oficial da Atividade 3](decisions/20260806_inicie_etl_clientes_orientacao.md) ampliou o projeto. A sequência detalhada, os gates e os aceites estão no [plano de implementação](activity-3/implementation-plan.md).

## Estado atual

- Núcleo Python offline: snapshots, diff, contratos, schema drift, SQL auditável, isolamento por fonte, health, logs seguros e testes; leitor Google read-only implementado com transporte HTTP isolado.
- Multi-source: duas fontes ficticias com schemas distintos e a mesma key textual foram validadas no PostgreSQL local; estado, history, runs, drift, lock, falha, retry, lifecycle e hold especifico permaneceram isolados por fonte. O lote sequencial agora produz resumo agregado sanitizado.
- Retenção/minimização: migration 4 aplicada e validada por catálogo no staging;
  nenhum purge, hold real ou sincronização foi executado neste deploy. Prazos legais,
  owner, backup e offboarding produtivo continuam decisões humanas.
- Baseline institucional: aplicada no staging em 2026-08-05 e reconciliada em 2026-08-06 por histórico, catálogo e Data API somente de leitura; cinco tabelas vazias, 27 constraints, 14 índices, RLS/grants coerentes e nenhuma policy.
- Migration incremental de estado raw: criada em 2026-08-06, aditiva, coberta por testes estruturais e comportamentais offline, validada em PostgreSQL local e aplicada ao staging em 2026-08-11; catálogo, grants mínimos e tabelas vazias foram confirmados somente por leitura.
- Raw integrado: validado no staging exclusivamente com a fixture fictícia; primeira carga, idempotência, update, tombstone, restore, reorder de linhas e schema drift completo preservaram identidade/estado. Permanecem ausentes: Star Schema, BI, RLS/RBAC hierárquico, e-mail, estudo completo de custos/free tiers, onboarding e Draw.io.
- Contrato analitico: caso ficticio de categoria/pontuacao, Star Schema minimo,
  grain, metricas, dimensoes, identidade, minimizacao, acesso futuro e BI MVP
  definidos; nenhum objeto analitico foi implementado.

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

Sequencia minima orientada a entrega:

1. `analytical_contract` - definido em 2026-09-03;
2. `analytical_schema` - proximo gate unico;
3. `analytical_transformation`;
4. `analytical_rbac`;
5. `bi_mvp`;
6. `scheduler_minimum`;
7. `e2e_final`;
8. `drawio_and_delivery`.

O proximo gate implementa somente o schema analitico local aprovado. Nao
autoriza transformacao, dashboard, scheduler, staging ou dados reais. Decisoes
empresariais continuam em
[open-decisions.md](activity-3/open-decisions.md).

Ficam explicitamente pos-entrega: executor de purge, scheduler de retencao,
canal administrativo de retencao, otimizacao de locks e producao avancada
(capacity plan, tuning, identidade/hierarquia reais e operacao continua).

## Checkpoint operacional de 2026-08-19

A política de retry e commit ambíguo passou por fault injection offline. `sync_runs.id` pode ser
gerado pelo cliente e reutilizado, portanto nenhuma migration nova foi criada. O gate segue aberto:
o teste PostgreSQL real de lock/rollback não executou por erro 500 do Docker Desktop. Próximo gate
único: recuperar o Supabase local e executar os testes `psycopg` opt-in.

Esse checkpoint é histórico: o gate PostgreSQL local e a compatibilidade remota
read-only foram concluídos em 2026-08-24.

## Checkpoint de retenção em 2026-08-25

As três migrations aplicadas foram auditadas sem conexão externa. O desenho
preserva current, runs ancoradas e reconciliação de outcome ambíguo; modela hold
institucional/por fonte, lifecycle, offboarding e evidência agregada. A proposta
conceitual da migration 4 adiciona duas tabelas pequenas e não embute prazos no
banco. Classificação: `retention_schema_design_validated`.

## Migration 4 validada localmente em 2026-08-25

As quatro migrations foram aplicadas por reset local. Lifecycle, holds,
`purge_runs`, catálogo, FKs, índices, RLS, zero policies e grants mínimos
passaram em testes PostgreSQL; `last_sync_run_id` permaneceu restritiva. Nenhum
purge, staging, Google, comando linked ou commit foi executado. Classificação:
`retention_schema_local_validated`.
