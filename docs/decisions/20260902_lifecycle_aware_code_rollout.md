# Fechamento do rollout lifecycle-aware

**Data:** 2026-09-02

## Decisão

Encerrar o rollout do código lifecycle-aware como validação offline após a
aplicação validada da Migration 4, sem presumir um runtime de staging
implantado nem iniciar sincronização.

## Motivo

O repositório PostgreSQL já lê `enabled` e `lifecycle_status` sob bloqueio de
leitura e recusa fonte não ativa com `source_inactive` antes de criar run ou
alterar raw. O banco aplica a mesma barreira a novas `sync_runs`.

## Evidência

Em 2026-09-02 passaram 51 testes unitários relacionados, `compileall`,
`check-docs` e `git diff --check`, todos offline.

## Limites

O fechamento não autoriza sincronização, implantação de runtime, purge, hold,
offboarding, SQL remoto ou produção. Operação regular requer decisão humana
de escopo própria.
