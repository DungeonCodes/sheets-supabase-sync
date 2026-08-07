# ADR 20260806: semântica raw da Fase 2A

## Decisão

A semântica desejada é uma combinação de histórico append-only por execução e estado atual por fonte/chave de negócio. Cada captura raw deve ser auditável, enquanto o estado atual deve permitir idempotência, alteração, exclusão lógica e restauração sem depender do número físico da linha.

Nesta Fase 2A, essa semântica foi implementada somente no domínio local e no dry-run. `raw_import_rows` da baseline é compatível apenas com captura por execução: sua unicidade é `(sync_run_id, source_row_number)`. Ele não impõe identidade por `(data_source_id, row_key_hash)`, não contém marcador de exclusão e não possui identidade de versão por conteúdo.

## Consequência

O schema remoto não é suficiente para a Fase 2B. Antes de qualquer escrita no staging, será necessária uma migration incremental revisada que forneça, sem alterar a baseline:

- estado atual único por fonte e `row_key_hash`;
- exclusão lógica/restauração;
- histórico/versionamento auditável por conteúdo;
- índices para recuperar o estado atual por fonte;
- compatibilidade com retenção, minimização de PII e restauração.

Nenhuma migration foi criada ou aplicada nesta decisão. O `raw_import_rows` existente não receberá escrita até que a revisão humana aprove a semântica e a migration incremental.

## Continuação

Ainda em 2026-08-06, a migration incremental foi projetada e criada em
[`20260806_raw_current_state_migration.md`](20260806_raw_current_state_migration.md), que separa
`public.raw_current_rows` (estado atual) de `public.raw_import_rows` (histórico). Ela permanece
**não aplicada** em qualquer ambiente e a Fase 2B continua aguardando autorização humana.

## Segurança e retenção

Payload raw pode conter PII em produção. A fixture desta fase é fictícia, mas retenção, minimização, anonimização e descarte continuam decisões abertas. Hashes não substituem controles de acesso nem classificação de dados.
