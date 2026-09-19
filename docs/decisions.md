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

## 2026-09-09

Data: 2026-09-09
Decisao: compor Google reader e core raw em um entrypoint staging dedicado, com
guard de destino, validacao fechada de source/lifecycle e reconciliacao efetiva
de commit ambiguo.
Motivo: permitir um gate remoto posterior sem reutilizar `apply-local`, duplicar
o pipeline ou aceitar configuracao persistida divergente.
Alternativas consideradas: script de demo independente e liberacao de host no
CLI local; ambas rejeitadas por contornarem contratos existentes.
Impacto esperado: dry-run sem writes e sync staging explicitamente confirmada,
mantendo production proibida. Detalhes em
`docs/decisions/20260909_staging_sync_composition.md`.
