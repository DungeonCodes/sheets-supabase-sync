# Roadmap

O [documento oficial da Atividade 3](decisions/20260806_inicie_etl_clientes_orientacao.md) ampliou o projeto. A sequência detalhada, os gates e os aceites estão no [plano de implementação](activity-3/implementation-plan.md).

## Estado atual

- Núcleo Python offline: snapshots, diff, contratos, schema drift, SQL auditável, isolamento por fonte, health, logs seguros e testes; leitor Google read-only implementado com transporte HTTP isolado.
- Baseline institucional: aplicada no staging em 2026-08-05 e reconciliada em 2026-08-06 por histórico, catálogo e Data API somente de leitura; cinco tabelas vazias, 27 constraints, 14 índices, RLS/grants coerentes e nenhuma policy.
- Migration incremental de estado raw: criada em 2026-08-06, aditiva, coberta por testes estruturais e comportamentais offline, validada em PostgreSQL local e aplicada ao staging em 2026-08-11; catálogo, grants mínimos e tabelas vazias foram confirmados somente por leitura.
- Raw integrado: validado no staging exclusivamente com a fixture fictícia em 2026-08-13; a primeira execução criou 5 estados e 5 inserts, e a repetição idêntica não criou novos eventos. Permanecem ausentes: staging/Star Schema, BI, RLS/RBAC hierárquico, e-mail, estudo completo de custos/free tiers, onboarding e Draw.io.

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

O ciclo controlado de update, tombstone, restore e reorder foi validado no
staging em 2026-08-17. O próximo gate passa a ser schema drift controlado da
fixture fictícia, mediante autorização humana específica.

O checkpoint parcial de schema drift bloqueou com segurança adição, remoção e
rename de header no staging, preservando o estado raw. Próximo passo: validar
reorder controlado de headers; header duplicado permanece no mesmo gate.
Decisões empresariais continuam em [open-decisions.md](activity-3/open-decisions.md); quase tempo
real, BI ou ferramenta adicional não devem ser presumidos.
