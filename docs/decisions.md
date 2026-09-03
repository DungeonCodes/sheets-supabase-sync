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
