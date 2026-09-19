# ADR 20260909: composicao segura Google para PostgreSQL staging

## Decisao

O fluxo remoto controlado e composto por `StagingSyncOrchestrator`, sem duplicar
leitura Google, snapshot, hashing, diff, tombstones, eventos ou persistencia. A
leitura Google e a validacao de PII terminam antes da abertura da transacao
PostgreSQL. O entrypoint dedicado oferece `dry-run` e `apply-staging`; somente o
segundo exige `--confirm-staging`. Production e ambientes desconhecidos nao
possuem override.

O guard valida em conjunto `APP_ENV`, project ref permitido, host da Data API e
a identidade do destino PostgreSQL. O banco deve ser o host direto do mesmo
projeto ou o Session Pooler identificado pelo usuario `postgres.<project_ref>`,
sempre na porta 5432 e database `postgres`. Nenhum desses identificadores e
exibido no resumo operacional.

## Source e lifecycle

Antes de cadastrar uma source, o repositorio procura conflitos por nome,
`target_table` ou par spreadsheet/aba. Uma source existente somente e aceita
quando nome, spreadsheet, aba, target e business key coincidem integralmente.
Qualquer divergencia falha fechada sem sobrescrever configuracao.

O schema atual persiste apenas `data_sources.enabled` como estado de lifecycle;
nao existem colunas de provider, slug separado, suspended, offboarding ou
retired. Por isso, o guard implementado considera `enabled=false` inativo e nao
inventa estados ou atributos ausentes. A verificacao ocorre sob advisory lock e
antes de `sync_run`, eventos ou current state.

## Retry e commit ambiguo

A politica existente de classificacao PostgreSQL e usada no fluxo real.
Tentativas retryable fazem rollback, readquirem o lock, recarregam source/current
e recalculam o diff. Erros non-retryable e lock ocupado nao sofrem retry.

Falha durante `COMMIT` e reconciliada em uma nova conexao pela mesma identidade
de execucao. Status/hash/contagens de `sync_runs`, quantidade de eventos e linhas
marcadas com `last_sync_run_id` devem ser coerentes:

- coerente e `applied`: sucesso reconciliado, sem novo evento;
- run ausente: tentativa controlada com a mesma identidade;
- divergente ou impossivel de consultar: `ambiguous_outcome`, falhando fechado.

## Dry-run e compatibilidade

O dry-run consulta somente a source e o current state, calcula o plano em memoria
e nao cadastra source, cria run ou persiste linhas. O caminho historico
`apply-local` permanece separado e continua recusando hosts remotos.

Este ADR registra apenas implementacao e testes offline. Nenhuma chamada Google,
conexao Supabase/PostgreSQL, migration ou sync real foi executada neste gate.
