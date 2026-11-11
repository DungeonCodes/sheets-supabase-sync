> A se??o **Pacote local preparado** ao final substitui o destino e o procedimento Supabase anteriores; hashes antigos de arquivos alterados s?o hist?ricos.

# RevisÃ£o consolidada para execuÃ§Ã£o SQL local

Data: 2026-11-11. Estado: **revisÃ£o humana e autorizaÃ§Ã£o de execuÃ§Ã£o pendentes**. Esta anÃ¡lise estÃ¡tica nÃ£o Ã© aprovaÃ§Ã£o, prova de sintaxe no servidor ou validaÃ§Ã£o de seguranÃ§a em execuÃ§Ã£o. Nenhum SQL foi executado neste trabalho.

## Escopo e destino

Projeto Supabase `sheets-supabase-sync`, sem link remoto. Destino proposto: instÃ¢ncia Docker nova deste projeto, PostgreSQL local via `127.0.0.1`, porta padrÃ£o esperada 54322, banco separado `analytics_fixture`. O `supabase start` tambÃ©m cria e migra o banco padrÃ£o da prÃ³pria stack, normalmente `postgres`: a revisÃ£o deve cobrir **ambos** os bancos e o seed automÃ¡tico. O nome `analytics_fixture` nÃ£o isola uma conexÃ£o se a porta ou host estiver errado. Antes de executar, verificar identidade do contÃªiner, cluster, endereÃ§o, banco, hashes e ausÃªncia de banco preexistente; se houver conflito, parar e investigar, sem sobrescrever.

`supabase/config.toml` contÃ©m somente `project_id`; os demais valores vÃªm da CLI e do ambiente. API, Auth, Studio e demais serviÃ§os usam defaults da versÃ£o instalada; nÃ£o foram validados em execuÃ§Ã£o. A CLI 2.98.2 pode inicializar serviÃ§os e SQL interno de plataforma alÃ©m dos arquivos abaixo. A documentaÃ§Ã£o atual dos defaults pode ter mudado desde essa versÃ£o. A stack pode conter serviÃ§os que tentam acessar rede para imagens ou funÃ§Ãµes opcionais; nÃ£o configurar fornecedores externos, Google, SMTP externo ou endpoints remotos. Impedir uso de credenciais do ambiente. ReferÃªncias: [configuraÃ§Ã£o oficial](https://supabase.com/docs/guides/local-development/cli/config), [rede em loopback](https://supabase.com/docs/guides/local-development).

DiagnÃ³stico sem SQL: Engine 29.9.3 em WSL 2 operacional, 12 CPUs, cerca de 7,7 GiB; um contÃªiner externo parado, nenhum volume listado, rede externa `security-scanner_default` preservada. Nenhuma escuta detectada nas portas 54320â€“54327, 54329, 3000 e 3218 no momento da inspeÃ§Ã£o. CLI 2.98.2, Python .venv 3.12.1, psycopg 3.3.4, Node 24.14.0. `psql` nÃ£o foi localizado no PATH. Esses fatos nÃ£o garantem disponibilidade futura ou bind seguro.

## InventÃ¡rio e hashes SHA-256

Ordem de aplicaÃ§Ã£o: as seis migrations listadas, seguidas do seed. Hashes dos bytes, nÃ£o de SQL normalizado:

| Ordem | Arquivo | SHA-256 |
|---|---|---|
| 1 | `supabase/migrations/20260804000000_initial_isolated_institution_schema.sql` | `35f26438baafe8f5b65bd12ff2136866e7c02d081e6e265fe371a3c676f1a034` |
| 2 | `supabase/migrations/20260806120000_add_raw_current_state.sql` | `58b001424ab1c4059545738164c631fc316f6065a95772d78823b7d407a77610` |
| 3 | `supabase/migrations/20260811150000_make_raw_import_event_only.sql` | `cf1d7f9419169ad4b8007b83e5188cb2c27d0a7ab12114dd6e632577b8dfe6de` |
| 4 | `supabase/migrations/20260825120000_add_retention_controls.sql` | `28e5e5d3f2484e80988d6547100e65c37b2405ae985673d0572dc4ea8c07eaed` |
| 5 | `supabase/migrations/20260903120000_add_analytics_star_schema.sql` | `a0ddad8e3468c4939e26e759b1059a1b3936e197439596bd604153bd23134783` |
| 6 | `supabase/migrations/20261111130000_analytics_refresh_candidate.sql` | `4039c9f7c7f3a81418a7fc59774b2e71b23731e6aa21e766bb477b2c7364e3a2` |
| seed | `supabase/seed.sql` | `6c31b49f4b190c14388d677952163ebacaf33d6477665d4ef80ae537c486d062` |

HÃ¡ SQL embutido em Python e TypeScript, portanto a lista de `.sql` nÃ£o Ã© a lista completa de instruÃ§Ãµes a executar. Arquivos de teste, repositÃ³rio e dashboard constam abaixo. O SQL interno distribuÃ­do nas imagens oficiais da CLI nÃ£o estÃ¡ inventariado por hash aqui. Qualquer alteraÃ§Ã£o apÃ³s revisÃ£o invalida a correspondÃªncia da aprovaÃ§Ã£o com os bytes atuais.

## Achados e riscos

### 1. Alto â€” descoberta de testes inclui SQL proibido

`scripts/test-integration.ps1:11` descobre `test_*postgres*.py`. `tests/integration/test_multi_source_postgres.py:59-72` apaga fisicamente fixtures no `tearDown`. `tests/integration/test_retention_controls_postgres.py:63-70,181-246,469-534,707-723` inclui `DELETE` fÃ­sico e `TRUNCATE`, alguns esperados como bem-sucedidos; outros sÃ£o testes de rejeiÃ§Ã£o em savepoint. A regra em `AGENTS.md` proÃ­be automaticamente `DELETE` fÃ­sico; rollback, fixture e intenÃ§Ã£o de testar rejeiÃ§Ã£o nÃ£o sÃ£o exceÃ§Ãµes. `TRUNCATE` tambÃ©m Ã© destrutivo e nÃ£o se enquadra nas autorizaÃ§Ãµes desta missÃ£o. **NÃ£o executar o script de descoberta ou essas operaÃ§Ãµes.** O teste de isolamento precisa ser adaptado para conservar fixtures sintÃ©ticas em banco dedicado; retenÃ§Ã£o destrutiva precisa de desenho separado que nÃ£o execute comandos proibidos. NÃ£o alegar cobertura desses cenÃ¡rios atÃ© existirem testes seguros e executados.

### 2. Alto â€” permissÃµes do dashboard e RBAC/RLS ainda nÃ£o definidos

Migration 5 habilita RLS sem policies e revoga permissÃµes de `public`, `anon`, `authenticated` e `service_role`, depois concede ao Ãºltimo uso do schema, SELECT/INSERT/UPDATE e uso de sequences. Migration 6 concede SELECT na allowlist e EXECUTE na funÃ§Ã£o a `service_role`. Isso **nÃ£o** cria papel de leitura do dashboard nem policies para as tabelas analÃ­ticas e pÃºblicas consultadas por `apps/dashboard/lib/data.ts:37-51`. Um teste como owner/superuser ou papel BYPASSRLS nÃ£o comprova isolamento por fonte. SÃ£o necessÃ¡rias especificaÃ§Ã£o e revisÃ£o de um papel local sem BYPASSRLS, grants mÃ­nimos, policies que garantam a fonte e testes positivos/negativos sob esse papel antes do E2E completo. NÃ£o usar superuser no dashboard nem expor conexÃ£o no navegador. NÃ£o foi preparada migration de RBAC: a polÃ­tica de identidade e isolamento por fonte ainda nÃ£o estÃ¡ definida neste escopo.

### 3. MÃ©dio â€” invoker e privilÃ©gios das funÃ§Ãµes de retenÃ§Ã£o

Migration 4 usa funÃ§Ãµes invoker com `search_path = pg_catalog, public`, sem SQL dinÃ¢mico ou `SECURITY DEFINER`; revoga EXECUTE de funÃ§Ãµes internas inclusive para `service_role`. Triggers chamam funÃ§Ãµes auxiliares tambÃ©m revogadas. A interaÃ§Ã£o real entre privilÃ©gios do invocador, funÃ§Ãµes auxiliares e grants de coluna exige teste com o papel efetivo: execuÃ§Ã£o como proprietÃ¡rio pode esconder erro de permissÃ£o. Revisar antes de conceder EXECUTE adicional; nÃ£o ampliar privilÃ©gios sem demonstrar necessidade.

### 4. MÃ©dio â€” limites de concorrÃªncia da transformaÃ§Ã£o

Migration 6 exige REPEATABLE READ ou SERIALIZABLE, bloqueia a linha `analytics.dim_source` com `FOR UPDATE`, e consulta raw sob snapshot estÃ¡vel. A allowlist Ã© por source; categorias invÃ¡lidas, score incompatÃ­vel ou hash invÃ¡lido abortam a transaÃ§Ã£o. Upserts sÃ£o condicionais e a reconciliaÃ§Ã£o compara contagens de ativos. A chave composta protege categoria pertencente Ã  mesma source. NÃ£o hÃ¡ integraÃ§Ã£o explÃ­cita entre o lock da transformaÃ§Ã£o e o advisory lock do sincronizador raw: snapshot consistente nÃ£o garante que um refresh reflita alteraÃ§Ãµes raw posteriores ao inÃ­cio da transaÃ§Ã£o. Conflitos de serializaÃ§Ã£o/retry e consistÃªncia concorrente requerem teste real. A reconciliaÃ§Ã£o por contagem nÃ£o comprova igualdade de valores individuais. NÃ£o hÃ¡ teste real de isolamento de papÃ©is nesta etapa.

### 5. MÃ©dio â€” bootstrap, diagnÃ³stico e alvo

`scripts/test-integration.ps1` usa a URL do banco padrÃ£o obtida por `supabase status`, nÃ£o `analytics_fixture`; retorna sucesso em alguns casos de SKIP e usa `try/catch` em processo nativo sem verificar explicitamente `$LASTEXITCODE`. Os testes PostgreSQL raw aceitam `LOCAL_DATABASE_URL` sem validaÃ§Ã£o de loopback no prÃ³prio teste. NÃ£o executar o script atual para aprovaÃ§Ã£o desta missÃ£o: preparar um executor fail-closed que valide host, porta, nome do banco, identidade do cluster e cÃ³digo de saÃ­da, selecione apenas testes permitidos e falhe em qualquer skip. As duas suÃ­tes analÃ­ticas validam host numÃ©rico e banco `analytics_fixture`, mas isso nÃ£o autentica a identidade do servidor.

## Efeitos das migrations e seed

1. **Baseline:** cria `public.data_sources`, `sync_runs`, `raw_import_rows`, `import_errors`, `schema_change_requests`, Ã­ndices, FKs e checks. Habilita RLS, revoga anon/authenticated e concede privilÃ©gios amplos a service_role inicialmente. Sem insert de dados.
2. **Raw atual:** cria `public.raw_current_rows` e trÃªs Ã­ndices, RLS e grants de SELECT/INSERT/UPDATE; adiciona `change_type`, `row_version` e checks no histÃ³rico. Sem backfill.
3. **Eventos:** um bloco verifica que `raw_import_rows` estÃ¡ vazio e aborta caso contrÃ¡rio. Remove trÃªs constraints e duas restriÃ§Ãµes NOT NULL, impÃµe NOT NULL em duas colunas, cria novas constraints de identidade e payload e restringe histÃ³rico a SELECT/INSERT. `DROP CONSTRAINT` e `DROP NOT NULL` sÃ£o alteraÃ§Ãµes de schema; nÃ£o sÃ£o `DROP COLUMN`, mas exigem revisÃ£o. A precondiÃ§Ã£o protege dados existentes contra conversÃ£o implÃ­cita e deve ser verificada no banco exato, nÃ£o inferida apenas do nome.
4. **RetenÃ§Ã£o:** adiciona lifecycle; `UPDATE public.data_sources ... WHERE NOT enabled` converte somente fontes desabilitadas em `suspended`, com metadados tÃ©cnicos. Em banco novo antes do seed, espera-se zero linhas, sujeito Ã  verificaÃ§Ã£o. Cria `retention_holds`, `purge_runs`, Ã­ndices, checks, funÃ§Ãµes e triggers para lifecycle, holds, evidÃªncia e locks; nÃ£o implementa purge fÃ­sico. Possui FKs `ON DELETE SET NULL`, triggers `BEFORE DELETE` e `BEFORE TRUNCATE`; nÃ£o sÃ£o em si comandos de exclusÃ£o, mas podem reagir a operaÃ§Ãµes futuras. Restringe privilÃ©gios operacionais. `purge_runs` permite registrar evidÃªncia de execuÃ§Ã£o destrutiva, nÃ£o executa exclusÃ£o por si.
5. **Analytics:** cria schema `analytics`, `dim_source`, `dim_category`, `fact_category_score`, Ã­ndices, FKs, checks e RLS. FKs `ON DELETE RESTRICT`; policies ausentes. Grants conforme achado 2.
6. **Candidata:** cria `analytics.category_allowlist` e `analytics.refresh_category_score(uuid)` SECURITY INVOKER, search_path fixo `pg_catalog, analytics, public`; revoga e concede privilÃ©gios explicitamente. Faz inserts/upserts condicionais em dimensÃµes e fatos e atualiza fatos ausentes para `is_current=false`. NÃ£o exclui dados fisicamente. NÃ£o hÃ¡ chamadas externas nem SQL dinÃ¢mico nas migrations identificadas. A instalaÃ§Ã£o de extensÃµes e SQL de plataforma da imagem nÃ£o foi auditada neste relatÃ³rio.
7. **Seed:** insere uma source com `spreadsheet_id='fixture'`, chave fictÃ­cia e `ON CONFLICT (name) DO NOTHING`; nÃ£o atualiza dados. Outro conflito em target ou identidade pode falhar. A repetiÃ§Ã£o nÃ£o garante correÃ§Ã£o da linha jÃ¡ existente. NÃ£o acessa Google.

Em geral DDL cria objetos com nomes fixos e nÃ£o Ã© idempotente em reaplicaÃ§Ã£o manual. O histÃ³rico de migrations da CLI evita reaplicaÃ§Ã£o normal, mas nÃ£o autoriza duplicar execuÃ§Ã£o manualmente. Falha transacional pode reverter a transaÃ§Ã£o corrente; nÃ£o presumir atomicidade de toda a inicializaÃ§Ã£o, nem que commits prÃ©vios serÃ£o desfeitos. Depois de commit, recuperaÃ§Ã£o requer restauraÃ§Ã£o de backup/revisÃ£o e migraÃ§Ã£o corretiva aditiva; nÃ£o automatizar DROP, reset, limpeza de volumes ou exclusÃ£o. Preservar evidÃªncias e pausar diante de estado parcial.

## SQL embutido e persistÃªncia dos testes

| Arquivo | SHA-256 | Efeitos e limites |
|---|---|---|
| `tests/integration/test_analytics_local.py` | `1b772af1277996791da293fd4c79b35dd08a87e6441e0e6a56cc91bfa0279279` | Inserts sintÃ©ticos em source, allowlist e raw; refresh, updates lÃ³gicos, savepoint e rollback no tearDown. Se `setUp` falhar antes do tearDown, fechamento/rollback deve ser confirmado. |
| `tests/integration/test_analytics_pipeline_local.py` | `fa33fcde15339421c50b21af3158078733c5956bf91d63c4f92a40f3f0e01211` | ServiÃ§o Python real, inserts/updates e refresh em transaÃ§Ãµes separadas; fixtures, dimensÃµes, fatos, runs e histÃ³rico persistem. Imprime source_ref sintÃ©tica. NÃ£o limpa. |
| `tests/integration/test_postgres_raw_repository.py` | `e4b691c81f4c79f2ca672e06e38d4b6f521fea2cc04afc5ef341b0589f895054` | Lifecycle, rollback, advisory lock, busy, retry e confirmaÃ§Ã£o ambÃ­gua; grava fixtures permanentes; nÃ£o restringe URL ao loopback. |
| `tests/integration/test_operational_postgres.py` | `e03d13301803ace306896c9f285218ea3c22492cfae6a32157edd8e3e4adee6b` | Consultas, advisory locks transacionais e rollback; nome de tabela dinÃ¢mico vem de tupla fixa. URL sem guard local. |
| `tests/integration/test_multi_source_postgres.py` | `e07499e02dbadd3f90717caf59c71c62cbe065ca59d9d5aeee73f3f359108eb6` | Inclui drift, falhas, hold e isolamento; `tearDown` usa DELETE fÃ­sico proibido. NÃ£o executar atÃ© corrigido. |
| `tests/integration/test_retention_controls_postgres.py` | `0d18ba9100940f295a6941803826eca8560cb348bdf8e606551ae11652021b19` | Inserts, updates, locks, testes de privilÃ©gios, savepoints, commits, DELETE e TRUNCATE. NÃ£o executar a suÃ­te completa. |
| `src/sheets_supabase_sync/raw_repository.py` | `72c083cb8af317c5a230b7cb2f269aa820bde253547fbd5ff4bbd8d779ff7c7f` | SELECT parametrizado, registro de source, runs, histÃ³rico e estado, updates de tombstone/restore, schema drift e advisory lock por hash. NÃ£o contÃ©m DELETE fÃ­sico no caminho revisado. Rollback e reconciliaÃ§Ã£o nÃ£o substituem teste real. |
| `apps/dashboard/lib/data.ts` | `fd917a281a17c9c5b18bfac72c5d0aeacfc81fb8ab427c6ed4c20875a292833b` | Quatro SELECTs parametrizados em transaÃ§Ã£o READ ONLY REPEATABLE READ; limita URL a loopback e `analytics_fixture` e exige token HTTP. NÃ£o estabelece por si privilÃ©gios/RLS. |
| `scripts/test-integration.ps1` | `25d22599d491b220cb0bbd3aabc3ffd427dda143b81c1164cce7b30fa996fa07` | **NÃ£o executar como estÃ¡**; descoberta inclui testes proibidos e SKIP pode retornar sucesso. |

Os testes nÃ£o sÃ£o demonstraÃ§Ã£o de RBAC quando executados com proprietÃ¡rio. A anÃ¡lise de SQL indireto Ã© limitada aos caminhos enumerados; bootstrap da CLI, dependÃªncias e scripts alternativos nÃ£o integram um manifesto de SQL completamente fechado. Para aprovaÃ§Ã£o vinculante Ã© preciso revisar tambÃ©m o procedimento e quaisquer arquivos novos usados para criar banco, grants e policies, com seus hashes.

## Procedimento pretendido apÃ³s revisÃ£o humana

1. Corrigir o executor e os testes proibidos; preparar SQL explÃ­cito de criaÃ§Ã£o do banco e de acesso de leitura, policies e regressÃµes. Adicionar seus hashes e revisar antes de executar. NÃ£o alterar migrations histÃ³ricas. Reconciliar o manifesto completo de SQL transitivo e versÃ£o das imagens.
2. Revalidar portas, contÃªineres, volumes e hashes; conferir ausÃªncia de recursos homÃ´nimos. Criar rede exclusiva sem tocar nas demais: `docker network create -o "com.docker.network.bridge.host_binding_ipv4=127.0.0.1" sheets-supabase-sync-local`. Conferir suas opÃ§Ãµes antes do uso. A documentaÃ§Ã£o oficial recomenda esse bind e `--network-id`; confirmar na versÃ£o 2.98.2 e inspecionar todas as portas publicadas depois. NÃ£o basta usar URL loopback se Docker publicar em interfaces externas.
3. Somente com revisÃ£o explÃ­cita do SQL de bootstrap e migrations: `supabase start --network-id sheets-supabase-sync-local`. O comando inicia serviÃ§os, pode baixar imagens e executa migrations e seed no banco padrÃ£o. NÃ£o imprimir saÃ­da de status com chaves; capturar e sanitizar. NÃ£o usar `--ignore-health-check` como prova de saÃºde.
4. Confirmar contÃªineres do projeto, healthchecks, bind em loopback, `pg_isready` e conexÃ£o local; verificar banco atual, histÃ³rico de migrations, objetos, constraints e contagem seed com consultas revisadas. Diagnosticar falha sem reset. NÃ£o rodar `supabase stop --no-backup` nem remover volume.
5. Criar `analytics_fixture` somente se comprovadamente ausente; preparar explicitamente extensÃµes, papÃ©is e objetos que migrations exigem nesse banco. A criaÃ§Ã£o de banco, seu template e como aplicar migrations/seed sem pular prÃ©-requisitos ainda nÃ£o estÃ£o especificados em SQL revisÃ¡vel: **nÃ£o hÃ¡ comando pronto seguro para esta etapa**. Aplicar arquivos revisados na ordem e registrar hashes, resultado e histÃ³rico separado. NÃ£o aplicar SQL de staging.
6. Executar testes selecionados de `test_postgres_raw_repository` e `test_operational_postgres` no banco dedicado apenas apÃ³s guard de destino e aprovaÃ§Ã£o de seu SQL; executar analytics local e pipeline com `RUN_ANALYTICS_LOCAL_TESTS=1` e URL numÃ©rica de `analytics_fixture`. Corrigir isolamento entre sources sem DELETE fÃ­sico e testar. Excluir e registrar casos de retenÃ§Ã£o proibidos. Falha ou qualquer skip Ã© inconclusivo, nÃ£o PASS. Verificar resultado de cada processo nativo e nÃºmero de testes.
7. Reconciliar por source contagens de raw ativo/tombstone, histÃ³rico por evento, runs e fatos correntes, incluindo update, falha, restore e segunda execuÃ§Ã£o; consultar apenas dados sintÃ©ticos. Pipeline analÃ­tico deixa dados persistentes e retorna source_ref para o dashboard. `tests/end_to_end/test_local_flow.py` Ã© marcador e nÃ£o evidencia E2E.
8. Preparar papel estritamente de leitura e RLS revisados; validar acesso permitido e negado sob esse papel, depois configurar token privado e URL local no processo servidor do Next.js. Executar `npx playwright test --config playwright.pg.config.ts` em `apps/dashboard`, que inicia em `127.0.0.1:3218`. Confirmar autenticaÃ§Ã£o, categorias e filtro, sem imprimir token ou URL. A demo histÃ³rica permanece intacta.
9. Registrar contagens, cÃ³digos de saÃ­da, versÃµes, identidade do banco, evidÃªncias de isolamento, pendÃªncias e arquivos alterados. NÃ£o remover dados nem volumes; nÃ£o conectar serviÃ§os externos.

## ConclusÃ£o

Auditoria estÃ¡tica identificou impedimentos reais; nÃ£o constitui revisÃ£o humana nem autorizaÃ§Ã£o. A lista do SQL da plataforma e o desenho do banco e RBAC ainda nÃ£o estÃ£o completos; portanto o pacote ainda nÃ£o Ã© um plano totalmente executÃ¡vel apÃ³s uma simples aprovaÃ§Ã£o. Ã‰ preciso preparar e revisar esses artefatos e adaptar testes sem aÃ§Ãµes destrutivas antes do E2E. Nenhuma migration, seed, teste SQL ou comando de criaÃ§Ã£o de banco foi executado.


## Pacote local preparado — substitui o procedimento Supabase anterior

O contêiner `sheets-sync-local-postgres` da imagem oficial `postgres:17.11-alpine3.23` está saudável, com banco inicial `analytics_fixture`, porta `127.0.0.1:55432` e volume `sheets-sync-local-pg-data`. O entrypoint inicializou o cluster e o banco; nenhuma migration, seed, papel ou SQL da aplicação foi executado. Nenhum SQL de projeto é montado automaticamente. Senha administrativa aleatória em `runtime/local-postgres-password.txt`, ignorado pelo Git; manter acesso ao arquivo e ao Docker restrito. PostgreSQL puro não equivale ao Supabase hospedado: Auth, API, padrões de privilégios Supabase, BYPASSRLS de service_role e serviços hospedados não foram reproduzidos. `gen_random_uuid()` é builtin no PostgreSQL 17 e as migrations não pedem extensão explícita.

Arquivos e hashes atuais para revisão: [review-manifest.json](../infra/local-postgres/review-manifest.json), 72 arquivos, SHA-256 do manifesto `77d658a61ece2ef21b1a8c0afb4e5b782546675ace0faee269e0b38a97087b78`. Ele contém as seis migrations e seed, os SQLs novos, código Python chamado, testes, runner, fixture e arquivos do dashboard. Os hashes de arquivos modificados nas seções antigas são históricos; o manifesto é a referência atual. Uma alteração exige rever e atualizar os hashes afetados. Executáveis Python, Node, pacotes instalados e camadas da imagem não estão congelados; a tag da imagem não está fixada por digest.

O banco é criado pelo entrypoint com `POSTGRES_DB=analytics_fixture`, não por SQL de aplicação. O runner verifica nome, usuário e porta e a ausência de `public.data_sources`. Sequência proposta:

1. `infra/local-postgres/01_compat_roles.sql`: exige o banco correto e cria `anon`, `authenticated`, `service_role` sem LOGIN ou BYPASSRLS e `dashboard_fixture` com LOGIN, sem superuser, CREATEDB, CREATEROLE ou BYPASSRLS. Esses papéis são globais no cluster dedicado, não em um único banco; não simulam integralmente o Supabase.
2. Seis migrations e `supabase/seed.sql`, na ordem e com efeitos descritos acima e hashes no manifesto. A terceira requer histórico vazio e a sexta continua candidata. O runner aplica os arquivos numa única transação por `local_admin`; a reversão diante de erro ainda requer validação real.
3. `infra/local-postgres/02_dashboard_rls.sql`: revoga TEMPORARY de PUBLIC no banco e CREATE de PUBLIC no schema público, restringe grants de tabelas e colunas e cria cinco policies SELECT vinculadas à source literal `fixture_dashboard`. O papel não recebe raw, DML, CREATE ou EXECUTE na transformação. A interface retorna agregados, mas o papel pode consultar linhas individuais de fatos dessa source. Não é política de produção ou isolamento multi-tenant geral.
4. O runner executa `ALTER ROLE dashboard_fixture PASSWORD <valor aleatório>` na mesma transação; gera a senha no processo, sem literal no repositório, e a salva depois em `runtime/local-dashboard-password.txt`. Se houver falha após commit, preservar o estado; o runner recusa reaplicação e não há limpeza automática.

O runner seleciona 12 testes reais: sete do repositório raw, dois operacionais, um analítico transacional, um pipeline e um de permissões do dashboard. Não seleciona `test_multi_source_postgres.py` ou retenção/purge, que contêm DELETE físico ou TRUNCATE. A fixture é `data/fixtures/multi_source_b.csv`; o pipeline grava source sintética com referência analítica fixa `fixture_dashboard`, allowlist e estado raw. O teste de permissões grava uma segunda source fictícia para comprovar que não é visível ao leitor. Pipeline e teste de permissões deixam fixtures persistentes; sequências também podem avançar após rollback. O teste de escrita negada tenta INSERT e CREATE como leitor, esperando erro de permissão; não executa DELETE ou TRUNCATE. Também verifica recusa de raw e da função e atributos do papel.

Playwright usa conexão de leitura no servidor Next.js, exige autenticação HTTP local e valida resposta 401 anônima, categorias, valores finais 12 e 20 e filtro. O processo navegador/Next não recebe as URLs administrativas do runner. Os outros estágios do ciclo são validados no PostgreSQL, não na tela em cada etapa. O teste de categoria inválida e rollback analítico usa savepoint na suíte analítica. O runner falha se não houver 12 testes, se algum for pulado, se PostgreSQL, migration ou teste de navegador falhar, ou se o navegador não registrar um teste aprovado. Resultados reais ainda não existem.

Comando somente após revisão e aprovação humana explícita deste pacote:

```powershell
.\.venv\Scripts\python.exe scripts/run-local-postgres-e2e.py --execute-reviewed
```

O runner verifica hashes, nome e label da instância, imagem, healthcheck, volume e bind; não aceita alvo configurável. Não executa reset nem reaplica automaticamente. A aprovação deve incluir SQL embutido e alteração de senha, e a revisão deve examinar o código e dependências. Em falha pós-commit o banco e dados sintéticos persistem; não reexecutar nem apagar volume sem plano separado. Não foi executado parser SQL de PostgreSQL nem conexão ao banco: sintaxe, transação, RLS, concorrência e compatibilidade ainda não foram verificadas em runtime. As policies podem requerer correção se os testes reais falharem.

Validação offline: Compose `config --quiet`, manifesto e inspeção do contêiner, 204 testes unitários, dois de contrato, build, typecheck, lint e três testes Playwright demo passaram. Quatro testes unitários verificam guardas do runner, incluindo skip e bind incorreto. Não equivalem ao E2E PostgreSQL nem à aprovação humana.

## 2026-11-11 — fechamento das regressões locais, aguardando autorização

O manifesto originalmente aprovado permanece SHA-256 `77d658a61ece2ef21b1a8c0afb4e5b782546675ace0faee269e0b38a97087b78`. Na comparação dos seus 72 arquivos, somente `tests/integration/test_postgres_raw_repository.py` divergiu: `e4b691c81f4c79f2ca672e06e38d4b6f521fea2cc04afc5ef341b0589f895054` para `aa038ec944dd53af353270e60ba8c231b22acb1288552d1f92556cf1660f40b3`. As migrations, seed, SQL de papéis/policies e runner original permaneceram idênticos. A versão do HEAD, convertida para CRLF, corresponde ao hash anteriormente aprovado do teste; análise de AST confirma que os literais com SQL da versão anterior e atual são iguais.

Caso A: falha injetada antes do commit é classificada por `RawSynchronizationService` como `SyncError` DATABASE não reexecutável, e o serviço chama rollback. A nova asserção verifica código e retryable e mantém a consulta que exige zero sources persistidas para cada um dos quatro pontos. A primeira execução abortou na primeira asserção antiga e não demonstrou essa consulta nem os outros três pontos. Estado final PostgreSQL e rollback completo ainda requerem a execução autorizada.

Caso B: `after_commit` ocorre depois de `connection.commit()`. Uma falha de conexão nessa etapa é classificada como ambígua; o serviço usa nova conexão somente de leitura e reconcilia por source e execution_id, hash, status, contagens de eventos e estado. Resultado APPLIED retorna sucesso reconciliado, não tenta nova transação de escrita; a asserção alterada exige esse resultado, uma invocação do ponto de falha, uma execução aplicada, um evento e versão 1. O teste anterior falhou antes das consultas finais; estado e contagens ainda não foram verificados nesta etapa. A reexecução cria fixtures UUID novas, não repete a identidade anterior; mantém os dados, sem limpeza.

O novo pacote está em `infra/local-postgres/regression-manifest.json`, SHA-256 `f85e74b6dea38f85fe73d53f3f1114cbfda7ea22575c7290a04b1189690206ad`, com os 72 arquivos anteriores, o manifesto original e `scripts/run-local-postgres-regression.py`. Além da alteração descrita no teste, este runner é novo; ele verifica o hash do novo manifesto, os 74 arquivos, contêiner, bind, volume e banco local; seleciona somente os dois testes e exige duas execuções sem skips. O SQL novo do runner é apenas a mesma consulta de identidade local usada no runner anterior: `select current_database(), current_user, inet_server_port()`. Não aplica migrations, seed, roles ou policies, nem usa reset, DELETE físico ou TRUNCATE.

Comando **somente após revisão humana e autorização explícita do manifesto novo**:

```powershell
.\.venv\Scripts\python.exe scripts/run-local-postgres-regression.py --manifest-sha256 f85e74b6dea38f85fe73d53f3f1114cbfda7ea22575c7290a04b1189690206ad --execute-reviewed
```

Manifesto e contêiner foram verificados sem SQL. Testes offline dos guards, incluindo rejeição de aprovação ausente, hash incorreto e skip, passaram. Nenhuma conexão PostgreSQL ou execução SQL ocorreu nesta etapa. O manifesto antigo foi preservado; a configuração Python/Next gerada pelo servidor local fica fora do novo manifesto e não muda SQL do pacote.
