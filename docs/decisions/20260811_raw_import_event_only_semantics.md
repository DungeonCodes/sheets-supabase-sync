# ADR 20260811: `raw_import_rows` como histórico event-only

## Decisão

`public.raw_current_rows` representa o estado atual: uma linha por identidade lógica da fonte.
`public.raw_import_rows` passa a representar somente eventos de negócio: primeira aparição,
alteração de conteúdo, tombstone e restauração. Cargas idênticas e simples reordenações de
`source_row_number` não criam evento no histórico.

## Contexto e incompatibilidade atual

A migration aplicada acrescentou `change_type` com CHECK que aceita somente `inserted`, `changed`,
`restored` e `unchanged`; portanto ela não pode registrar o evento `tombstone` exigido por esta
decisão. Além disso, `raw_import_rows.source_row_number` é obrigatório e único por `sync_run`.
Um tombstone é inferido pela ausência de uma linha e não possui número físico de origem seguro;
reutilizar o último número pode colidir com uma reordenação.

O código atual também não possui adaptador PostgreSQL executável: `PostgresRawRepository` apenas
declara SQL, enquanto o serviço usa a implementação em memória. Logo não existe ainda uma
unidade transacional integrada Google → PostgreSQL que adquira lock, crie `sync_run`, persista
eventos/estado, finalize e comite atomicamente.

## Consequência

A terceira migration `20260811150000_make_raw_import_event_only.sql` implementa o contrato sem
alterar as duas migrations aplicadas. Ela torna `source_row_number`, `content_hash` e `payload_json`
anuláveis apenas no tombstone, substitui a unicidade física por
`(sync_run_id, data_source_id, row_key_hash)` e restringe os eventos aos quatro tipos aprovados.
Uma precondição aborta a migration se o histórico não estiver vazio, evitando conversão silenciosa.

O adaptador PostgreSQL usa `psycopg` e uma transação única. A leitura Google ocorre antes da
transação; depois do advisory lock transacional, o estado atual é recarregado e o diff definitivo
é calculado. `sync_run`, eventos, estado e finalização são confirmados em um commit; qualquer
falha reverte tudo. A migration e o adaptador foram validados somente no Supabase local e ainda
não foram aplicados ao staging.

## Retenção e LGPD

O histórico event-only reduz crescimento e duplicação de payload em execuções idênticas. Ainda
assim, eventos de alteração e tombstone podem conter PII; retenção, minimização, anonimização e
descarte continuam pendentes antes de uso produtivo.

## Deploy no staging

Em 2026-08-11, a terceira migration foi aplicada sozinha ao staging apos validacao local. A
introspecao read-only confirmou o contrato event-only, RLS, zero policies, grants minimos e todas
as tabelas operacionais vazias. Nenhuma leitura Google, sincronizacao ou insercao de fixture fez
parte do deploy.
