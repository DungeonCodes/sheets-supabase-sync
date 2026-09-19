# ADR 20260819: politica de retry operacional e commit ambiguo

## Decisao

Falhas usam quatro disposicoes: `retryable`, `non_retryable`, `busy_deferred` e
`ambiguous_outcome`. PostgreSQL e classificado por SQLSTATE/tipo e estagio. `40001` e `40P01`
permitem nova transacao completa. Classe `08`, timeout, DNS ou TCP antes do `COMMIT` permitem retry
limitado; durante `COMMIT`, produzem `ambiguous_outcome`. Classes `28`, `3D` e `42` nao sofrem retry.
Lock ocupado e deferred, sem espera e sem `sync_run`.

Cada execucao gera uma UUID cliente e reutiliza a identidade em todas as tentativas. O schema atual
suporta isso por `sync_runs.id`; nao e necessaria migration. Cada retry readquire lock, rele o estado
e recalcula o diff. Commit ambiguo nunca dispara retry automatico.

## Reconciliacao

Consultar o primario por `(sync_runs.id, data_source_id)` e comparar `status`, `snapshot_hash` e
contagens. Se `applied` for coerente, reconciliar eventos por `sync_run_id` e estado por
`last_sync_run_id`. Ausencia, `running` ou divergencia mantem o resultado desconhecido e nao autoriza
repeticao cega.

## Observabilidade e limite

Logs aceitam apenas prefixo da fonte, operacao, tentativa, maximo, categoria, retryable, backoff,
duracao e outcome. `import_errors` permanece para erro de fonte/linha/dado, nao falha operacional.
Fault injection offline e PostgreSQL local passaram em 2026-08-24: lock, busy,
rollback, retry idempotente e commit ambíguo foram exercitados com fixtures
fictícias. Esta evidência é somente local; não afirma validação em staging.
