# Decisoes

## Formato

Data:
Decisão:
Motivo:
Alternativas consideradas:
Impacto esperado:

## 2026-08-19

Data: 2026-08-19
Decisão: quatro disposições operacionais e `sync_runs.id` cliente-gerado como identidade de execução.
Motivo: impedir retry cego de commit desconhecido e forçar releitura/diff em retries seguros.
Alternativas consideradas: classificação por mensagem e nova migration de idempotência.
Impacto esperado: retry limitado e reconciliação sem migration adicional.

## 2026-09-02

Data: 2026-09-02
Decisao: validar duas fontes independentes por `data_source_id` no mesmo projeto institucional.
Motivo: comprovar isolamento de identidade, schema, estado, lock e falha antes da camada analitica.
Alternativas consideradas: criar nova migration, paralelizar o lote ou criar segunda fonte no staging.
Impacto esperado: execucao sequencial multi-source com resumo agregado, sem DDL ou multi-tenancy.

## 2026-09-03

Data: 2026-09-03
Decisao: adotar para a entrega um Star Schema corrente e minimo de
categoria/pontuacao, conforme
`docs/decisions/20260903_minimum_analytical_contract.md`.
Motivo: demonstrar raw para analytics para BI com grain e metricas objetivos,
sem inventar dominio real nem promover payload ou PII desnecessaria.
Alternativas consideradas: Snowflake, history analitico, `DIM_DATE`, modelo
generico e uniao estrutural de fontes incompativeis.
Impacto esperado: proximo gate limitado a duas dimensoes e uma fato locais;
RBAC, dashboard e operacao produtiva permanecem gates posteriores.
