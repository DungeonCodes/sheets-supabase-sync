# Arquitetura

Cada instituicao possui um projeto Supabase independente. `data_sources` descreve uma planilha e uma aba; cada fonte tem uma `target_table` espelho propria e nao possui relacionamento automatico com outras tabelas espelho.

O pacote separa dominio (`sources`, `identifiers`, `mirror_schema`, `scheduling`), orquestracao (`orchestration`, `synchronizer`), persistencia SQL (`sql_generator`, `executors`) e bordas locais (`cli`, arquivos de configuracao e fixtures). O dominio nao depende de CLI, Google, Supabase, psql ou sistema de arquivos.

Na Fase 1, `google_sheets` contém somente o modelo determinístico, parsing e orquestração da leitura; `google_transport` é a borda HTTP GET autenticada; `google_config` valida configuração e credencial externa. O transporte implementa uma interface local pequena e pode ser substituído por fake nos testes. O leitor não importa Supabase, não gera SQL, não transforma regras de negócio e não persiste dados.

As tabelas operacionais `data_sources`, `sync_runs`, `raw_import_rows`, `import_errors` e `schema_change_requests` fornecem trilha de auditoria e usam chaves estrangeiras somente entre si. Dados brutos ficam em JSONB tanto na tabela espelho quanto em `raw_import_rows`.

## Baseline do banco

A migration ativa `20260804000000_initial_isolated_institution_schema.sql` cria somente as cinco tabelas operacionais. As tabelas espelho nao fazem parte da baseline: cada uma sera proposta e criada posteriormente pelo sincronizador, em modo explicito, sem foreign keys para outras tabelas espelho.

As migrations anteriores da PoC foram arquivadas antes do primeiro deploy e nunca foram aplicadas. A primeira tentativa da baseline consolidada falhou com `SQLSTATE 42601` porque `current_schema` conflitava com um identificador especial do PostgreSQL. A transacao sofreu rollback completo e nao foi registrada no historico remoto.

O campo agora se chama `previous_schema`: ele armazena o estado anterior conhecido usado na comparacao, enquanto `proposed_schema` registra a proposta detectada. Em 2026-08-05, testes, lint e dry-run listaram somente a baseline corrigida, que foi aplicada com sucesso ao staging. O historico local e remoto registra a mesma versao; as cinco tabelas operacionais estao vazias e nenhuma tabela espelho foi criada. A baseline aplicada e imutavel e toda evolucao devera ocorrer por migration incremental.

Em 2026-08-06, nova inspecao independente e somente de leitura confirmou esse estado diretamente: cinco tabelas, 27 constraints, 14 indices, zero linhas, nenhuma tabela espelho, `previous_schema` presente e campos obsoletos/multitenant ausentes. RLS, policies, grants e Data API tambem foram verificados sem escrita.
