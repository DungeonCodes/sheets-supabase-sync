# Registro de Execução

## Formato

Data:
Ação realizada:
Arquivos alterados:
Resultado:
Pendências:
Próximo passo:

## 2026-08-06 — auditoria da Atividade 3

Data: 2026-08-06

Ação realizada: leitura integral da fonte oficial e inventário local; extração de 40 requisitos; análise de lacunas; plano Fases 0–8; riscos, decisões e gates.

Arquivos alterados: somente documentação em `README.md` e `docs/`.

Resultado: rastreabilidade atualizada sem implementar funcionalidades, aplicar SQL, acessar banco remoto ou ler segredos; `compileall` aprovado; 63 testes executados, 4 pulados e nenhuma falha; `check-docs` e `git diff --check` aprovados.

Pendências: decisões OD-01–OD-15, pesquisa temporal de quotas/custos e execução futura dos gates.

Próximo passo: concluir, sob revisão humana, a validação segura da baseline corrigida no staging; depois executar o MVP ponta a ponta com dados fictícios.

## 2026-08-06 — reconciliação somente de leitura do staging

Data: 2026-08-06

Ação realizada: validação sanitizada do ambiente staging e vínculo permitido; autenticação CLI; inspeção somente de leitura de migrations, catálogo, constraints, índices, RLS, policies, grants, contagens e Data API.

Comandos de escrita: nenhum. `db push`, reset vinculado, repair, seed e SQL de escrita não foram executados.

Resultado: histórico `baseline_applied`; uma migration local e uma remota na versão `20260804000000`, sem pendência ou divergência. Catálogo com cinco tabelas operacionais, 27 constraints (12 checks, 6 FKs, 5 PKs e 4 uniques), 14 índices, `previous_schema` presente, colunas obsoletas ausentes, RLS nas cinco tabelas, zero policies, grants esperados e zero linhas. Data API respondeu HTTP 200. Classificação final: `baseline_applied_validated`.

Limitação: o dump schema-only não executou por indisponibilidade do Docker; o arquivo temporário vazio foi removido. A inspeção equivalente foi concluída com `supabase db query --linked` usando apenas `SELECT`, `inspect db` e geração de tipos.

Validação final: `compileall` aprovado; 63 testes executados, 59 aprovados, 4 pulados e nenhuma falha; `check-docs`, `git diff --check` e a repetição de `migration list` aprovados.

Pendências: validação humana formal do checkpoint; integração local permanece pulada sem Docker/`psql`; requisitos hierárquicos de RLS/RBAC continuam parciais.

Próximo passo: iniciar Fase 1 — Google Sheets API com planilha fictícia.

## 2026-08-06 — implementação local da Fase 1 Google Sheets

Autorizada e instalada exclusivamente no `.venv` a dependência `google-auth[requests]==2.56.3`; `pip check` e importações oficiais passaram, sem lockfile adotado no repositório. Foi implementado leitor HTTP v4 somente GET com Service Account e escopo único `spreadsheets.readonly`, configuração externa, representação determinística, validação de cabeçalho/fixture, erros tipados, timeout e retry com backoff, jitter, orçamento e `Retry-After`. Logs e diagnóstico exibem apenas estados, categorias, duração e contagens.

Quotas oficiais foram consultadas em 2026-08-06 e registradas em `docs/activity-3/google-sheets-api-limits.md`. A suíte local passou com 93 testes, dos quais 5 integrações foram puladas. Nenhuma chamada Google real foi executada neste checkpoint porque o ID e a aba da fixture não estavam configurados e a confirmação humana não foi fornecida; nenhuma escrita Google ou Supabase ocorreu.

Próximo gate único: executar e registrar a leitura read-only da planilha privada fictícia com `verify-google-sheets.py --confirm-fictitious` no `.venv`.

## 2026-08-06 — tentativa de integração real Google Sheets

Confirmação humana registrada: fixture privada, exclusivamente fictícia, sem dados pessoais e compartilhada como Leitor. A baseline local passou com 93 testes, 5 skips e zero falhas; credencial externa, variáveis e escopo único read-only foram confirmados sem exibir valores.

O diagnóstico pelo `.venv` obteve contexto de autenticação em memória, mas o GET inicial de metadados respondeu 403, categoria sanitizada `authorization`, em aproximadamente 1,8 segundo e uma tentativa. O teste opt-in reproduziu o mesmo erro em aproximadamente 1,6 segundo. Uma tentativa de isolar configuração ausente no PowerShell removeu a variável de processo e herdou o valor do arquivo, causando um terceiro GET read-only com o mesmo 403; nenhuma outra chamada remota foi feita. Hash sanitizado da fonte: `9caa6c8b788a`.

Resultado: zero abas, colunas, linhas ou células retornadas; nenhum retry; nenhuma escrita Google/Supabase; nenhum segredo, URL ou identificador completo exibido. Cenários locais de configuração ausente, aba inexistente, cabeçalho duplicado, timeout, 429 e sanitização passaram por mocks. `ING-03` permanece `implemented_not_validated` e a Fase 1 segue aberta.

Próximo gate único: revisão externa da habilitação da API, correspondência da Service Account compartilhada e fixture configurada; depois repetir o diagnóstico read-only. Fase 2 não iniciada.

## 2026-08-06 — integração Google Sheets aprovada

Após a habilitação manual da Sheets API e o ajuste do nome da aba, o diagnóstico read-only passou no `.venv`: autenticação aprovada, planilha acessível, uma aba encontrada, 7 colunas, 5 linhas, zero linhas vazias, zero retries e duração de 1.913 ms. O teste de integração Google opt-in passou em 1.534 s.

Nenhum conteúdo de célula, cabeçalho, token, URL, ID completo ou e-mail foi exibido. Nenhuma escrita Google ou Supabase ocorreu. A evidência comprova `ING-03` como `partially_validated` no escopo da fixture fictícia; quotas, scheduler, múltiplas fontes e persistência continuam fora da Fase 1.

Fase 1 encerrada no escopo aprovado da leitura Google. Próximo marco: Fase 2 — persistência raw e sincronização idempotente no Supabase staging, ainda sem execução nesta tarefa.

## 2026-08-06 — Fase 2A raw e idempotência local

Foi avaliada a baseline aplicada sem executar SQL remoto. `raw_import_rows` registra captura por execução, mas sua unicidade é apenas por execução/número de linha; não há estado único por fonte/chave, tombstone ou identidade de versão. A lacuna bloqueia a Fase 2B e está registrada na ADR `20260806_phase_2a_raw_semantics.md`; nenhuma migration foi criada.

O domínio local produziu snapshot e hashes determinísticos, diff por chave de negócio configurável, tombstones, plano de primeira carga, lock sem espera e rollback in-memory. O dry-run read-only da fixture retornou 5 linhas lidas, 5 novas, zero alteradas/removidas/restauradas/inalteradas e zero persistidas, em 1.686 ms. Apenas hashes prefixados foram exibidos; não houve acesso ou escrita no Supabase.

Próximo gate único: revisão e autorização humana de uma migration incremental de estado raw. A Fase 2B não foi iniciada.

## 2026-08-06 — migration incremental de estado raw criada e não aplicada

Foi projetada, criada e validada localmente a migration incremental
`20260806120000_add_raw_current_state.sql`. Ela é aditiva: cria `public.raw_current_rows` com
identidade única por fonte e chave de negócio, exclusão lógica, restauração, versionamento,
janela de observação e vínculo com a execução; e acrescenta apenas as colunas opcionais
`change_type` e `row_version` a `public.raw_import_rows`. Não há `DROP`, `TRUNCATE`, `DELETE FROM`,
`ALTER COLUMN` ou renomeação. A baseline `20260804000000` não foi editada e um teste de digest
SHA-256 passa a impedir alteração retroativa.

A decisão de separar histórico e estado atual foi registrada na ADR
`20260806_raw_current_state_migration.md`. Eventos de exclusão não são anexados ao histórico porque
não são observados na planilha e colidiriam com a unicidade `(sync_run_id, source_row_number)` da
baseline aplicada.

O pacote recebeu o módulo de domínio `raw_state`, que traduz o plano de mudanças em transições de
estado, e `raw_repository` passou a expor os comandos parametrizados de carga, inserção,
atualização, tombstone, restauração e observação, além da avaliação de schema orientada à nova
tabela. O serviço passou a separar histórico append-only de estado atual e a registrar evento
sanitizado de sucesso e de falha.

Validação local: `compileall` aprovado; 141 testes executados, 136 aprovados, 5 pulados e nenhuma
falha; `check-docs` e `git diff --check` aprovados. Inspeção remota somente de leitura:
`migration list` mostrou duas migrations locais e uma remota, sem divergência; `db lint --linked`
não encontrou erro de schema; `db push --dry-run` listou somente a migration incremental. O lint
incide sobre o schema remoto atual e, portanto, não valida o DDL novo.

O dry-run real da fixture fictícia foi repetido em modo somente leitura: 7 colunas, 5 linhas, zero
linhas vazias, zero retries, 5 novas, zero alteradas/removidas/restauradas/inalteradas, 5 comandos
de inserção de estado e zero persistidas, em 1.571 ms. Hash sanitizado da fonte: `0540648fa393`.
Nenhum cabeçalho, célula, identificador completo, token ou URL foi exibido.

Pendências: o DDL não foi executado em PostgreSQL real porque Docker e `psql` estão ausentes nesta
máquina e nenhuma infraestrutura foi instalada; o teste de integração local permanece bloqueado.
Nenhuma escrita remota ocorreu e nenhum commit foi executado.

Próximo gate único: revisão humana do DDL incremental e autorização explícita da Fase 2B. A Fase 2B
não foi iniciada.

## 2026-08-11 — validação local PostgreSQL bloqueada durante provisionamento

Os gates de ambiente passaram: Docker Client e Server 29.7.2, daemon Docker Desktop no backend
Linux/WSL2 acessível, e Supabase CLI 2.90.0 disponível. `supabase start` foi executado apenas
contra o ambiente local, mas excedeu 124 segundos sem concluir. A inspeção posterior mostrou seis
imagens Supabase baixadas e nenhum container; em particular, `supabase_db_sheets-supabase-sync` não
existia. Portanto, o bloqueio foi classificado como provisionamento/download incompleto de imagens,
não como falha de migration, schema ou SQL.

Nenhum reset, SQL local, acesso remoto, escrita no staging ou alteração de migration foi realizado.
As fases de PostgreSQL real, testes automáticos opt-in e as verificações remotas read-only/dry-run
não foram iniciadas, pois dependem de `supabase start` concluído.

Próximo gate único: concluir `supabase start` local com o container de banco saudável e retomar a
validação a partir da Fase 3.

## 2026-08-11 — validação PostgreSQL local concluída, grant incompatível encontrado

O provisionamento local anteriormente incompleto terminou com sucesso manualmente; PostgreSQL local
ficou saudável. As migrations `20260804000000` e `20260806120000` foram confirmadas no catálogo
local, na ordem esperada. O DDL, PK, duas FKs, UNIQUE, sete CHECKs, RLS habilitado e zero policies
foram confirmados em PostgreSQL real. Fixtures exclusivamente fictícias, descartadas por rollback,
comprovaram inserção, idempotência, alteração, tombstone, restauração, reordenação, rejeições
de constraints/FK, rollback e advisory lock concorrente sem espera.

Falha de gate: embora `anon` e `authenticated` não tenham acesso, `service_role` tem DELETE efetivo
em `raw_current_rows`, além de SELECT/INSERT/UPDATE. A migration concede apenas os três últimos,
mas não revoga privilégios preexistentes; portanto ela requer correção incremental antes de staging.

A suíte offline passou com 141 testes, 136 aprovados, 5 pulados e zero falhas; os opt-in existentes
para PostgreSQL permaneceram pulados porque `psql` não existe no host. `migration list`, `db lint
--linked` e `db push --dry-run` foram executados somente em leitura/dry-run: duas migrations locais,
uma remota, lint sem erro e somente a incremental pendente. Nenhuma escrita no staging, push, reset
linked, repair ou commit foi executado.

Classificação: `requires_changes`. Próximo gate único: revisar e aprovar uma nova migration
incremental que revogue DELETE de `service_role`, depois repetir a validação local de grants.

## 2026-08-11 — correção de menor privilégio na migration pendente

O privilégio excessivo foi atribuído aos default privileges locais do ambiente Supabase: a tabela
nova herdava `arwdDxtm` para `service_role`. Não houve membership de role, policy, função SECURITY
DEFINER ou grant em outra migration que explicasse o acesso. A própria migration pendente
`20260806120000_add_raw_current_state.sql` foi corrigida, sem terceira migration: ela agora revoga
todos os privilégios de PUBLIC, anon, authenticated e service_role na tabela específica e concede
somente SELECT/INSERT/UPDATE a service_role.

`supabase db reset` executou apenas localmente e reaplicou baseline e incremental. No PostgreSQL
real, service_role tem SELECT/INSERT/UPDATE e não tem DELETE/TRUNCATE/REFERENCES/TRIGGER/MAINTAIN;
anon e authenticated não têm acesso, RLS está habilitado e policies são zero. Testes sob
service_role comprovaram as permissões positivas e as negações; fixtures foram revertidas. A
regressão de ciclo raw, rollback e advisory lock passou. A suíte offline (141, 136 aprovados, 5
pulados), lint e dry-run passaram; o remoto continua com somente esta migration pendente.

Classificação: `approved_for_staging`. Nenhuma escrita no staging, push, repair ou commit ocorreu.
Próximo gate único: aprovação humana para executar a migration pendente no staging.

## 2026-08-11 — migration incremental aplicada ao staging

Após gates finais verdes, `20260806120000_add_raw_current_state.sql` foi a única migration
aplicada ao staging vinculado e permitido. O histórico ficou com duas migrations locais e duas
remotas, sem pendência ou divergência. Inspeção remota somente leitura confirmou
`raw_current_rows` com 14 colunas, PK, UNIQUE, duas FKs, oito CHECKs, os três índices previstos,
RLS habilitado e zero policies.

Os grants remotos efetivos agora são SELECT/INSERT/UPDATE apenas para service_role; DELETE,
TRUNCATE, REFERENCES, TRIGGER e MAINTAIN são negados, assim como qualquer acesso para anon e
authenticated. Contagens agregadas confirmaram zero linhas em `raw_current_rows` e nas demais
tabelas operacionais; nenhum dado real ou fixture foi inserido. Lint final e suíte offline passaram.

A Fase 2B de sincronização permanece não executada. Próximo gate único: sincronização
controlada da fixture exclusivamente fictícia, após autorização humana própria.

## 2026-08-11 — gate de primeira sincronização integrada requer mudanças

A semântica aprovada para este gate define `raw_current_rows` como estado atual e
`raw_import_rows` como histórico event-only: somente inserção, alteração, tombstone e
restauração devem gerar eventos. A ADR `20260811_raw_import_event_only_semantics.md` registra que
o schema aplicado não aceita `tombstone` em `change_type` e que o número de linha obrigatório por
execução torna o evento inferido ambíguo em reordenações.

Também foi confirmado que não há adaptador PostgreSQL executável nem caminho Google → banco:
o repositório declara SQL, mas o serviço integrado persiste somente em memória. Assim, lock,
transação, `sync_run` e rollback não podem ser comprovados para uma escrita remota. Nenhuma leitura
Google adicional, escrita no staging ou alteração de fixture foi executada.

Classificação: `requires_changes`. Próximo gate único: aprovar o desenho e a implementação
local do adaptador transacional e da evolução de schema para tombstone event-only.

## 2026-08-11 — event-only e adaptador PostgreSQL validados localmente

Foi criada somente a terceira migration `20260811150000_make_raw_import_event_only.sql`. As duas
migrations aplicadas permaneceram intactas. O schema local agora usa identidade lógica por
execução/fonte/chave, permite `source_row_number` nulo no tombstone, não inventa conteúdo/payload e
restringe o histórico a insert/update/tombstone/restore. RLS foi preservado e service_role recebe
somente SELECT/INSERT no histórico.

Foi adicionado `psycopg[binary] 3.3.4` e implementado o adaptador transacional. O snapshot externo
é preparado antes da transação; lock, leitura do estado, diff, run, eventos, estado e finalização
ocorrem atomicamente. Três testes PostgreSQL reais comprovaram primeira carga de cinco linhas,
idempotência, update, tombstone sem linha/payload inventado, restore, reorder sem evento, quatro
rollback points e locks concorrentes por fonte.

O reset local aplicou 3 migrations. A suíte executou 150 testes, 142 aprovados, 8 pulados e zero
falhas; os 3 testes PostgreSQL opt-in passaram separadamente. O remoto permaneceu 2/2, lint sem
erro e dry-run somente da terceira migration. Nenhuma escrita no staging ou Google ocorreu.

Classificação: `approved_for_staging`. Próximo gate único: revisão humana e autorização para
aplicar exclusivamente a terceira migration no staging vazio.

## Deploy da migration event-only no staging em 2026-08-11

Após os gates locais aprovados, foi aplicada exclusivamente a migration
`20260811150000_make_raw_import_event_only.sql` no staging vinculado permitido.
O histórico ficou alinhado em 3/3. A introspecção somente-leitura confirmou o
contrato event-only, a unicidade lógica, RLS e grants sem regressão; as tabelas
operacionais permaneceram vazias. Não houve leitura Google, sincronização ou
inserção de fixture nesta execução.

Classificação: `deployed_validated`. Próximo gate único: primeira sincronização
integrada controlada da fixture fictícia, mediante autorização específica.

## Gate de sincronização integrada interrompido em 2026-08-11

A leitura real da fixture fictícia foi aprovada com 5 linhas e 7 colunas, sem
retries, conteúdo exibido ou dados pessoais detectados. O dry-run gerou 5 novos
estados e 5 eventos insert, sem persistência. A primeira tentativa autorizada
de abrir a conexão PostgreSQL direta para staging falhou na resolução de rede
do endpoint configurado, antes de adquirir lock ou iniciar transação.

As consultas remotas somente-leitura confirmaram que as seis tabelas
operacionais continuam em zero. Não houve sync_run, data_source, evento,
estado, import_error, escrita Google ou alteração da fixture.

Classificação: `blocked`. Próximo gate único: disponibilizar conectividade
PostgreSQL direta ao staging para o adaptador transacional, sem alterar dados.
