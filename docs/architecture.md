# Arquitetura

Cada instituicao possui um projeto Supabase independente. `data_sources` descreve uma planilha e uma aba; cada fonte tem uma `target_table` espelho propria e nao possui relacionamento automatico com outras tabelas espelho.

O pacote separa dominio (`sources`, `identifiers`, `mirror_schema`, `scheduling`), orquestracao (`orchestration`, `synchronizer`), persistencia SQL (`sql_generator`, `executors`) e bordas locais (`cli`, arquivos de configuracao e fixtures). O dominio nao depende de CLI, Google, Supabase, psql ou sistema de arquivos.

As tabelas operacionais `data_sources`, `sync_runs`, `raw_import_rows`, `import_errors` e `schema_change_requests` fornecem trilha de auditoria e usam chaves estrangeiras somente entre si. Dados brutos ficam em JSONB tanto na tabela espelho quanto em `raw_import_rows`.
