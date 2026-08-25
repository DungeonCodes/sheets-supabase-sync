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
