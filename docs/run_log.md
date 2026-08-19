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

## 2026-08-12 — gate de conectividade PostgreSQL bloqueado

Foi repetida somente a preparação sanitizada do gate de conectividade PostgreSQL, sem abrir conexão,
executar SQL, acessar Google, sincronizar ou alterar `.env.local`. O mecanismo da aplicação
(`load_environment`) requer `.env.local` na raiz; o arquivo não estava presente e não havia variáveis
de processo correspondentes para sobreposição. Assim, não foi possível confirmar se o endpoint era
Direct ou Session Pooler, nem validar a porta 5432.

O Python 3.12 disponível também não continha `psycopg` ou `psycopg-binary`, portanto a exigência
`psycopg[binary]==3.3.4` não pôde ser satisfeita. Nenhuma conexão PostgreSQL foi aberta; não foram
executados `SELECT`, `BEGIN`, locks, `ROLLBACK`, migrations ou comandos de escrita. Nenhum commit foi
executado.

Resultado: `blocked`. Próximo passo: restaurar a configuração privada local no caminho esperado e
disponibilizar `psycopg[binary]==3.3.4` no ambiente Python da aplicação; então repetir exclusivamente
este gate.

## 2026-08-19 — política de retry operacional implementada offline

Preflight confirmou branch `dev` e alteração preexistente apenas neste run log. A `.venv` ausente foi
criada com Python 3.12. A baseline revelou digest de teste desatualizado para a baseline corrigida já
presente no histórico Git; o guardrail foi alinhado ao SHA-256 versionado, sem editar migration.

Foram implementadas quatro disposições, classificação PostgreSQL por SQLSTATE/tipo/estágio, conexão
com retry limitado, UUID cliente em `sync_runs.id`, nova tentativa com releitura/diff e logs allowlist.
Fault injection comprovou rollback, retry, exaustão, ausência de duplicação, versão única e commit
desconhecido sem retry automático. `import_errors` não foi reutilizada. Nenhuma migration foi criada.

O Supabase local não iniciou: Docker Desktop retornou API 500. Os testes `psycopg` reais ficaram
bloqueados. Não houve Google real, staging, sincronização remota, migration remota ou fault injection
remoto. Classificação: `blocked`. Próximo gate único: recuperar o Supabase local e executar apenas os
testes operacionais opt-in via `psycopg`.

Validação final local: `compileall`, 157 testes (150 aprovados, 7 pulados, zero falhas),
`check-docs.py` e `git diff --check` aprovados.
