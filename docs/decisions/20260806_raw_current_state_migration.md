# ADR 20260806: migration incremental de estado raw

## Contexto

A [ADR de semântica raw](20260806_phase_2a_raw_semantics.md) registrou que a Fase 2A implementou
histórico append-only e estado atual apenas no domínio local. A baseline aplicada
`20260804000000_initial_isolated_institution_schema.sql` é imutável e sua tabela
`public.raw_import_rows` tem unicidade `(sync_run_id, source_row_number)`: ela representa a captura
por execução, mas não impõe identidade por `(data_source_id, row_key_hash)`, não possui marcador de
exclusão lógica e não versiona o estado.

## Decisão

Criar a migration incremental, aditiva e não destrutiva
`20260806120000_add_raw_current_state.sql`, que introduz `public.raw_current_rows` como tabela
separada de estado atual e mantém `public.raw_import_rows` como histórico.

### Por que uma tabela separada

1. As duas responsabilidades têm cardinalidade diferente: o histórico cresce por execução, o estado
   atual tem no máximo uma linha por fonte e chave de negócio.
2. Sobrecarregar `raw_import_rows` exigiria uma segunda unicidade `(data_source_id, row_key_hash)`
   que entraria em conflito direto com a unicidade `(sync_run_id, source_row_number)` já aplicada:
   a mesma linha física não pode ser simultaneamente "uma observação por execução" e "uma versão
   por chave".
3. Retenção diverge: o histórico é candidato natural a poda por idade; o estado atual precisa
   sobreviver enquanto a chave existir. Uma tabela única impediria políticas independentes (R-04).
4. A alternativa de acrescentar as capacidades a `raw_import_rows` exigiria alterar constraints da
   baseline aplicada, o que é proibido.

### Alteração aditiva no histórico

`raw_import_rows` recebe apenas duas colunas opcionais — `change_type` e `row_version` — para
classificar a observação e apontar a versão de estado resultante. Nenhuma coluna existente é
alterada, removida ou renomeada, e ambas aceitam `NULL`, portanto o DDL é compatível com a baseline
e com um banco sem dados.

Eventos de exclusão **não** são anexados ao histórico. A exclusão não é observada na planilha: ela é
inferida da ausência da chave. Reaproveitar o último `source_row_number` conhecido para gravar um
tombstone no histórico colidiria com `unique (sync_run_id, source_row_number)` sempre que outra
chave passasse a ocupar aquela posição na mesma execução. A exclusão fica registrada em
`raw_current_rows` (`is_deleted`, `deleted_at`, `version`, `last_sync_run_id`) e no contador
`sync_runs.deleted_rows`. Por isso `change_type` admite somente `inserted`, `changed`, `restored` e
`unchanged`, e a coluna `is_deleted` não foi adicionada ao histórico: seria uma coluna morta.

## Semântica das operações

| Operação | Estado atual | Histórico |
| --- | --- | --- |
| Primeira carga | insere com `version = 1`, `is_deleted = false`, `deleted_at` nulo | `inserted` |
| Carga idêntica | atualiza `last_seen_at` e `source_row_number`; `version`, `content_hash` e `updated_at` inalterados | `unchanged` |
| Alteração | atualiza `content_hash`/`payload_json`, incrementa `version`, mantém a identidade | `changed` |
| Exclusão | mantém a linha, marca `is_deleted`, preenche `deleted_at`, incrementa `version`, preserva o último conteúdo conhecido | não anexa |
| Restauração | limpa `deleted_at`, volta `is_deleted` para falso, atualiza conteúdo e incrementa `version` | `restored` |
| Reordenação | atualiza somente `source_row_number`; `content_hash` e `version` permanecem | `unchanged` |

`updated_at` acompanha mudanças de conteúdo ou de estado; `last_seen_at` acompanha observação. Essa
separação é deliberada: uma carga idêntica não deve parecer uma alteração de negócio.

## Consequências

- A Fase 2B deixa de estar bloqueada pelo schema, mas continua bloqueada por autorização humana: a
  migration foi criada e validada localmente e **não** foi aplicada em nenhum ambiente.
- `assess_raw_schema` passa a exigir as capacidades de `raw_current_rows`; a baseline sozinha
  continua sendo avaliada como insuficiente.
- O `service_role` recebe `select, insert, update` na nova tabela, sem `delete`: a exclusão nesta
  camada é sempre lógica e qualquer remoção física exige procedimento revisado.
- Retenção, minimização e anonimização continuam decisões abertas; a nova tabela mantém payload
  bruto e, em produção, esse payload pode conter dados pessoais.

## Decisão posterior

A semântica de histórico por observação desta ADR foi substituída em 2026-08-11 pela ADR
`20260811_raw_import_event_only_semantics.md`. O estado atual continua válido, mas o histórico passa
a registrar somente insert/update/tombstone/restore; carga idêntica e reordenação não geram evento.
