# Validacao multi-source local

**Data:** 2026-09-02

## Decisao

Validar multiplas fontes dentro de um unico projeto institucional sem adotar
multi-tenancy. Cada fonte conserva configuracao, schema, snapshot, estado e
execucao proprios. O lote permanece sequencial e passa a expor resumo agregado
sanitizado.

## Motivo

As tabelas operacionais ja usam `data_source_id`, current possui unicidade por
fonte e key, e o lock transacional recebe uma referencia por fonte. A prova com
duas fixtures demonstrou isolamento sem exigir DDL ou paralelismo.

## Evidencia

`SOURCE_A` e `SOURCE_B` usaram schemas diferentes e a mesma business key
textual. PostgreSQL local confirmou current/history/runs, drift, lock,
rollback, retry, lifecycle e hold especifico independentes. O batch continuou
apos falha e resumiu sucesso, falha, busy e inactive. As migrations locais
permaneceram 4/4.

## Limites

Nao houve segunda fonte em staging, acesso Google real, scheduler, purge,
relacao entre mirrors, `organization_id` ou alteracao de producao.
