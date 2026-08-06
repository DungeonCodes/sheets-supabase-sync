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
