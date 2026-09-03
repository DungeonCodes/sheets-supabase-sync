# Arquitetura

Cada instituicao possui um projeto Supabase independente. `data_sources` descreve uma planilha e uma aba; cada fonte tem uma `target_table` espelho propria e nao possui relacionamento automatico com outras tabelas espelho.

## Isolamento multi-source

Uma instituicao pode declarar varias fontes no mesmo projeto por `sources[]`.
Cada par `spreadsheet_id` + `sheet_name` e cada `target_table` devem ser unicos
na configuracao institucional. Estado, historico, runs, erros e requests de
schema sao particionados por `data_source_id`; a identidade raw e
`(data_source_id, row_key_hash)`. Assim, a mesma business key textual pode
existir em fontes distintas sem colisao. Snapshots e schemas sao mantidos por
fonte, e o advisory lock usa a referencia deterministica da fonte, permitindo
que A bloqueie outra execucao de A sem bloquear B.

O lote e sequencial e isola falhas por fonte. Seu resumo contem apenas totais
de sucesso, falha, busy e inactive; eventos operacionais usam `source_ref`
curta e nao incluem planilha, celulas ou payload. Isso nao introduz
multi-tenancy: o limite institucional continua sendo um projeto Supabase.

O pacote separa dominio (`sources`, `identifiers`, `mirror_schema`, `scheduling`), orquestracao (`orchestration`, `synchronizer`), persistencia SQL (`sql_generator`, `executors`) e bordas locais (`cli`, arquivos de configuracao e fixtures). O dominio nao depende de CLI, Google, Supabase, psql ou sistema de arquivos.

Na Fase 1, `google_sheets` contém somente o modelo determinístico, parsing e orquestração da leitura; `google_transport` é a borda HTTP GET autenticada; `google_config` valida configuração e credencial externa. O transporte implementa uma interface local pequena e pode ser substituído por fake nos testes. O leitor não importa Supabase, não gera SQL, não transforma regras de negócio e não persiste dados.

`raw_sync` concentra contrato, hashes, snapshots e diff sem rede; `raw_state` traduz um plano de mudanças em transições de estado atual; `raw_sync_service` coordena dry-run e transação; `raw_repository` isola avaliação de schema e comandos PostgreSQL parametrizados. A semântica combina histórico append-only com estado atual por fonte/chave. O adaptador usa `psycopg` e, no staging autorizado, conecta pelo Supavisor Session Pooler na porta 5432.

As tabelas operacionais `data_sources`, `sync_runs`, `raw_import_rows`, `import_errors` e `schema_change_requests` fornecem trilha de auditoria e usam chaves estrangeiras somente entre si. Dados brutos ficam em JSONB tanto na tabela espelho quanto em `raw_import_rows`.

## Histórico e estado atual

A separação está registrada na [ADR de migration incremental](decisions/20260806_raw_current_state_migration.md):

- `public.raw_import_rows` é o histórico append-only de eventos de negócio: `insert`, `update`, `tombstone` e `restore`. Tombstones não inventam posição, hash ou payload; a unicidade protege a identidade do evento por execução, fonte e chave.
- `public.raw_current_rows` é o estado atual, com no máximo uma linha por `(data_source_id, row_key_hash)`. Ela carrega `content_hash`, `payload_json`, `source_row_number`, `is_deleted`, `deleted_at`, `version`, `first_seen_at`, `last_seen_at` e `last_sync_run_id`, permitindo idempotência, exclusão lógica, restauração e comparação eficiente na execução seguinte.

Índices da nova tabela e a consulta que justifica cada um:

| Índice | Consulta justificadora |
| --- | --- |
| `raw_current_rows_source_key_unique` (constraint) | identidade e recuperação por `(data_source_id, row_key_hash)`; alvo de conflito das operações de estado |
| `raw_current_rows_active_idx` | varredura do estado ativo de uma fonte e detecção de linhas não observadas na última execução |
| `raw_current_rows_tombstone_idx` | inventário de tombstones por fonte para retenção, restauração e procedimento LGPD |
| `raw_current_rows_last_run_idx` | reconciliação das linhas afetadas por uma execução |

Nenhum índice duplica a chave primária ou a unicidade.

## Retenção e ciclo de vida

A migration local `20260825120000_add_retention_controls.sql`, definida na
[ADR de retenção](decisions/20260825_retention_schema_design.md), adiciona
lifecycle a `data_sources`, `retention_holds` e `purge_runs`. Prazos permanecem
em configuração externa versionada por fonte. A migration foi validada no
PostgreSQL local e aplicada de forma controlada ao staging.

Retenção histórica não inclui `raw_current_rows`. A FK
`raw_current_rows.last_sync_run_id` permanece restritiva: a run ancorada pelo
estado atual não pode ser removida. Offboarding é o único fluxo que poderá
eliminar current, sempre após suspensão, revogação externa de credenciais,
hold check e aprovação humana. `sync_runs` continua reservada à ingestão;
`purge_runs` preserva apenas evidência agregada, sem payload ou lista de IDs.

## Baseline do banco

A migration ativa `20260804000000_initial_isolated_institution_schema.sql` cria somente as cinco tabelas operacionais. As tabelas espelho nao fazem parte da baseline: cada uma sera proposta e criada posteriormente pelo sincronizador, em modo explicito, sem foreign keys para outras tabelas espelho.

As migrations anteriores da PoC foram arquivadas antes do primeiro deploy e nunca foram aplicadas. A primeira tentativa da baseline consolidada falhou com `SQLSTATE 42601` porque `current_schema` conflitava com um identificador especial do PostgreSQL. A transacao sofreu rollback completo e nao foi registrada no historico remoto.

O campo agora se chama `previous_schema`: ele armazena o estado anterior conhecido usado na comparacao, enquanto `proposed_schema` registra a proposta detectada. Em 2026-08-05, testes, lint e dry-run listaram somente a baseline corrigida, que foi aplicada com sucesso ao staging. O historico local e remoto registra a mesma versao; as cinco tabelas operacionais estao vazias e nenhuma tabela espelho foi criada. A baseline aplicada e imutavel e toda evolucao devera ocorrer por migration incremental.

Em 2026-08-06, nova inspecao independente e somente de leitura confirmou esse estado diretamente: cinco tabelas, 27 constraints, 14 indices, zero linhas, nenhuma tabela espelho, `previous_schema` presente e campos obsoletos/multitenant ausentes. RLS, policies, grants e Data API tambem foram verificados sem escrita.

Em 2026-08-06 foi criada a migration incremental `20260806120000_add_raw_current_state.sql`. Ela é aditiva, não contém operação destrutiva e foi aplicada ao staging em 2026-08-11. A terceira migration consolidou o histórico event-only no mesmo dia. A baseline não foi editada e um teste de digest garante essa imutabilidade.
