# Registro de Execução

## 2026-10-20 — GITHUB_CLOCK_SINGLE_MANUAL_DISPATCH (GREEN, autorização consumida)

Autorização humana explícita: armar temporariamente opt-in, uma tentativa manual
do relógio main, um dispatch para executor dev/staging, observar/reconciliar e
desarmar; sem recorrência. Execução GitHub CLI autenticada como DungeonCodes.
Worktree original dev em c6d13b686eb060bc4c3c6defdd5663c57861d4f4; preservadas
as mudanças locais existentes em run_log e SINGLE_DISPATCH_PREFLIGHT.md.

### Preflight final e baseline READ ONLY

Em 2026-10-20T18:49:46.605Z, GETs GitHub confirmaram exatamente os SHAs aprovados:
main 80cdde4bb79506deecb3d37f0e9894fba03739ac;
dev c6d13b686eb060bc4c3c6defdd5663c57861d4f4. Clock 390540622 ativo, blob
2e4f176567d6b5a038dcc0d00f9b6f938475d7ee, zero runs, próximo run_number 1.
Executor 388468858 ativo, blob 65d16e28a9e00918a0eac2213ab57b0e73fc6ea0,
uma run histórica GREEN e nenhuma concorrente. Nenhum schedule ou relógio extra.
Ambas as variables ausentes. Environment staging com política exclusiva branch
dev; sete nomes de secrets conferidos, sem acessar valores ou alterá-los.

Guard staging local PASS, project_ref corresponde à allowlist. Leitor e seleção
existentes usados sem modificar código; transações READ ONLY, rollback e
timeouts limitados, TLS cliente ativo. Dry-selection: total=1/due=1/executed=0,
failed=0/skipped=0/busy_deferred=0. Nenhuma chamada Google local ou apply local.

Baseline em 18:50:07.728866Z e reconferida em 18:50:10.410820Z: sync_runs=9,
raw_import_rows=11, raw_current_rows=8, planned/running=0. Escopo autorizado:
uma fonte, 3 runs, 3 eventos e 3 estados. Último sucesso 19/10 11:48:49.361510Z.
Fingerprint agregado de hashes de chave/conteúdo, versão e flag de exclusão:
2955c6490ddec36688043aafc3e36cb5. Deltas do dry-select zero.

### Opt-in e única tentativa

Após nova conferência de SHA/runs/variables, configuradas somente as duas
repository variables autorizadas. Leitura em 18:50:27.644Z confirmou:
STAGING_CLOCK_ENABLED=true e STAGING_CLOCK_AUTHORIZED_RUN_NUMBER=1.
Nenhuma secret, workflow, environment ou permissão global alterado; nenhum PAT.

Única chamada `gh workflow run staging-clock.yml`, repo fixo, ref main, iniciada
em **18:50:45.576Z**, com confirm_dispatch=true, expected_dev_sha aprovado e
approval_expires_at **2026-10-20T19:00:45.576Z**, calculado naquele instante
(10 minutos). Nenhum token nos inputs; nenhuma repetição, rerun ou dispatch
direto do executor. A resposta foi aceita e a run encontrada por leitura.

Clock run_id **39478296467**, workflow 390540622, run_number **1**, attempt **1**,
event workflow_dispatch, main e SHA aprovado. Criada em 18:50:47Z; completed/
success em 18:50:57Z. Job clock 118819918808, todos os steps success. Logs
processados só em memória; campos allowlisted, sem logs brutos ou tokens salvos.
Permissões efetivamente emitidas: **Actions: write e Contents: read**, conferidas
no setup do job. Confirma o token automático do relógio nesta execução.

Registros sanitizados do clock:

- 18:50:53.601Z: exatamente um dispatch_attempt_started, main/dev e SHAs aprovados;
  dispatch_started_at=18:50:53.595Z.
- 18:50:54.760Z: dispatch_http_response **HTTP 200**.
- 18:50:55.022Z: dispatch_accepted_not_completed, executor_run_id **39478314244**,
  dev/SHA esperado e attempt conferidos pelo código do clock.

Aceitação foi tratada separadamente da conclusão do executor. Contagem final:
um registro de tentativa POST e um filho aceito, compatíveis com a única run e
única tentativa permitidas pelo código revisado. Não é garantia exactly-once
contra outros atores externos.

### Desativação confirmada

Após capturar clock terminal e filho, ambas as variables foram removidas pelo
CLI. GET em **18:51:17.257Z** confirmou **STAGING_CLOCK_ENABLED=UNSET** e
**STAGING_CLOCK_AUTHORIZED_RUN_NUMBER=UNSET**, restaurando o estado anterior.
Nenhuma desativação prematura; clock já havia terminado. Estado repetidamente
confirmado no encerramento, sem autorização residual de disparo/recorrência.

### Executor e reconciliação

Executor run_id **39478314244**, workflow 388468858, run_number 2, attempt 1,
event workflow_dispatch, **dev/c6d13b686eb060bc4c3c6defdd5663c57861d4f4**.
Criado em 18:50:54Z, job dispatch 118819977179 de 18:50:59Z a 18:51:15Z,
completed/success. Checkout, setup Python, instalação do projeto, materialização
efêmera, staging guard, dispatcher e cleanup: todos success. Versão patch do
Python não extraída; não inferida de outros runs.

Deployment **7208288746**, environment **staging**, ref **dev**, SHA aprovado;
status success em 18:51:15Z, URL de status/log vinculada à run filha. Nenhum
environment ou credencial foi transferido ao clock. Proteção continua por branch,
não identidade de arquivo de workflow.

Resumo do dispatcher extraído de uma única linha do step correto, aceitando o
mascaramento do nome staging nos logs e sem persistir conteúdo privado:
sources_total=1, sources_due=1, **sources_executed=1**, **sources_no_changes=1**,
sources_skipped=0, **sources_failed=0**, **sources_busy_deferred=0**. Resultado
individual no_changes. Sucesso não foi inferido somente de exit code/GitHub verde.

Reconciliação efetiva em **18:52:19.317192Z**, PostgreSQL staging READ ONLY/TLS,
guard conferido antes da conexão:

| Métrica | Antes | Depois | Delta |
|---|---:|---:|---:|
| sync_runs global | 9 | 10 | +1 |
| raw_import_rows global | 11 | 11 | 0 |
| raw_current_rows global | 8 | 8 | 0 |
| planned/running global | 0 | 0 | 0 |
| sync_runs da fonte autorizada | 3 | 4 | +1 |
| eventos da fonte autorizada | 3 | 3 | 0 |
| estados atuais da fonte autorizada | 3 | 3 | 0 |

Exatamente **uma nova sync_run**, pertencente à fonte autorizada, status **applied**,
início/fim 2026-10-20T18:51:11.015751Z, inserts=0, updates=0, tombstones=0,
restores=0 e unchanged=3. Nenhuma run nova de outra fonte. Fonte enabled=true,
lifecycle_status=active, consecutive_failures=0. Fingerprint do estado idêntico
ao baseline: 2955c6490ddec36688043aafc3e36cb5. Efeitos no_changes medidos,
sem presumir estado da planilha antes da execução. Nenhuma divergência inesperada.

Conferência final **18:52:46.764Z**: uma única run total de clock, duas do executor
(uma histórica e uma nova), ambas novas completed/success/attempt 1, zero runs
ativas, ambas variables UNSET e schedule_enabled=false. Helper offline existente
classificou **GREEN** com identidade, contadores, guard e reconciliação verificados.

### Resultado e limites

GATE_RESULT=GITHUB_CLOCK_SINGLE_MANUAL_DISPATCH, **GREEN**. Autorização consumida.
Risco residual LOW: correlação PostgreSQL é por janela/fonte e ausência de
concorrência, não vínculo GitHub run_id persistido em sync_runs; fingerprint cobre
os atributos descritos, não cada coluna. TLS ativo não adiciona prova nova de
identidade do servidor. Uma execução manual não valida entrega schedule/SLA,
inatividade pública ou comportamento recorrente. Gates GREEN anteriores preservados.

Somente docs/run_log.md atualizado por esta execução; demais mudanças locais
anteriores preservadas. Sem modificação de código/workflows/secrets/environment,
PAT, produção, migration, Cron, extensão, Edge, benchmark, commit ou push.
Nenhum schedule habilitado. Próximo gate proposto:
**GITHUB_CLOCK_RECURRENCE_READINESS_REVIEW**, sem ativação automática.

Evidências GitHub:
[clock](https://github.com/DungeonCodes/sheets-supabase-sync/actions/runs/39478296467)
e [executor](https://github.com/DungeonCodes/sheets-supabase-sync/actions/runs/39478314244).

## 2026-10-20 — GITHUB_CLOCK_SINGLE_MANUAL_DISPATCH_PREFLIGHT (GREEN somente leitura)

Host DESKTOP-VU6VMS6, raiz sheets-supabase-sync, dev/HEAD
c6d13b686eb060bc4c3c6defdd5663c57861d4f4, inicialmente limpa e igual à remota.
Main remoto 80cdde4bb79506deecb3d37f0e9894fba03739ac. Clock publicado ativo,
workflow ID 390540622, blob idêntico ao manual testado, sem schedule. Zero runs
de clock, próximo número esperado 1; nenhum clock/executor concorrente. Executor
388468858 ativo, única run anterior 39247320871 completed/success, preservada.
Confirmação repetida ao final das leituras GitHub.

Repository variables STAGING_CLOCK_ENABLED e STAGING_CLOCK_AUTHORIZED_RUN_NUMBER
ausentes (sem valor; bloqueio esperado), nenhuma alterada. Default token read,
workflow job explicitamente actions:write/contents:read. Suporte documental e
configuração confirmados, token realmente emitido só poderá ser observado no
teste autorizado futuro. Staging segue com única regra branch dev; sete nomes
de secrets confirmados sem valores. Nenhuma alteração de permissions/secrets.

Dry-selection real, local e READ ONLY pelo entrypoint existente, uma config de
demonstração autorizada: total=1/due=1/executed=0/failed=0/skipped=0/busy=0.
Guard staging PASS, project_ref corresponde à allowlist; conexões com READ ONLY,
TLS ativo, timeouts limitados. Nenhuma chamada Google ou execução apply. Não
modificado código: inspeções auxiliares temporárias em memória, saída allowlist.

Baseline antes 2026-10-20T13:29:04.713099Z, depois 13:29:07.468940Z: globais
sync_runs=9/raw_import_rows=11/raw_current_rows=8/planned_running=0; deltas zero.
Escopo configurado: uma fonte, 3 runs/3 eventos/3 estados, último sucesso
2026-10-19T11:48:49.361510Z; fingerprint agregado de hashes/versão/flag de exclusão
2955c6490ddec36688043aafc3e36cb5 idêntico antes/depois. Sem payloads/credenciais.

Preparado procedimento futuro para autorizar número 1/opt-in, expiração UTC +10
min e uma única invocação main, observar parent/child, classificar falhas por
fonte apesar de exit code 0, desarmar e reconciliar staging. Comandos somente
documentados, não executados. Inputs SHA/expiração e baseline precisam nova
checagem imediatamente antes de executar. Resposta ambígua implica leitura e
interrupção sem retry. Config secreta remota não pode ser comparada por valor.

[Relatório e procedimento](../drafts/github_scheduler/SINGLE_DISPATCH_PREFLIGHT.md).
Somente documentação alterada. Nenhum clock/executor, variable mutation,
schedule, secret, produção, migration, código, commit ou push. Próxima aprovação:
APROVAR UM DISPARO MANUAL DO RELÓGIO, incluindo armar/desarmar temporariamente
as variables, sem autorização implícita neste gate.

## 2026-10-20 — GITHUB_CLOCK_MANUAL_PUBLICATION (GREEN, checkpoint humano)

Preflight atual: DESKTOP-VU6VMS6, raiz sheets-supabase-sync, branch dev em
4e595d6a5d2f8a9897cb6a5c8998f977aa85b554, inicialmente limpa. Origin/dev
coincide por ls-remote; origin/main coincide com referência local em
88ae3008140905ce05a4fcf7c01bc6db72db6c78. Checkpoint humano anterior incorporado;
nenhum SHA antigo presumido. Regras/contexto e candidato aprovados relidos.

GETs GitHub: main padrão, token default read; só workflows CI e executor manual
ativos. Main contém somente ci.yml e scheduled-sync.yml, nos blobs já revisados;
nenhum relógio equivalente registrado. Executor dev permanece ativo com blob
65d16e28a9e00918a0eac2213ab57b0e73fc6ea0. Staging continua com única política
branch dev; nenhuma repository variable de enable/autorização existe. Sem mudança
remota, secrets ou ambiente; nenhuma run disparada. Disponibilidade operacional
do executor é estado ativo/configuração preservada, não nova sync comprobatória.

Conforme autorização explícita deste gate, criada worktree isolada:
C:/Users/tisap/Documents/GitHub/sheets-supabase-sync-clock-publication,
branch prepare/github-clock-manual-publication, base origin/main no SHA acima.
Único arquivo transportado, byte a byte do candidato:
.github/workflows/staging-clock.yml, 157 linhas, blob
2e4f176567d6b5a038dcc0d00f9b6f938475d7ee. Executor, Python e demais arquivos
da worktree inalterados. YAML ainda não rastreado, sem git add/commit; o diff
normal da branch é vazio porque não houve commit. Escopo conferido pela união
diff origin/main e ls-files --others: somente o YAML. Patch completo de novo
arquivo preservado em drafts/github_scheduler/staging-clock-publication.patch
nesta worktree original dev, fora da branch isolada.

150 testes offline PASS (143 Node + 7 dispatcher). Igualdade byte a byte com
o draft testado, parser PyYAML 6.0.3 já instalado e estrutura YAML PASS;
gatilho único workflow_dispatch, permissões job actions:write/contents:read,
inputs restritos, sem environment/secrets de dados. Scan de credenciais PASS.
git diff --check e verificação no-index do arquivo novo PASS (aviso LF/CRLF).
Uma tentativa inicial de validação inline teve erro de quoting do shell;
reexecutada por stdin, sem mudanças no YAML, com todas as verificações aprovadas.

Publicação por si só não executa clock/sync; opt-in e autorização por número de
run permanecem ausentes. Push/PR futuros poderão acionar somente o CI já existente,
distinto do relógio. Riscos preservados: actions:write amplo, dev móvel, concorrência
externa e ambiguidade; proteção staging é por branch, não identidade de workflow.

Plano humano: revisar patch, fazer staging/commit somente desse YAML na branch
isolada, push dessa branch, PR com base main e conferência de um único arquivo;
aprovar/merge manualmente apenas após autorização específica. Nenhum PR criado.
Depois conferir publicação manual inerte, sem habilitar variables ou executar.
Rollback futuro desabilita apenas clock/opt-in e acompanha filhos eventualmente
aceitos, preservando executor/secrets. Próximo gate GITHUB_CLOCK_SINGLE_MANUAL_DISPATCH
exige autorização separada; publicação não concede autorização de dispatch.

Nenhum commit, push, PR, merge, workflow real, schedule, secret, PAT, alteração
environment, SQL, produção, Python, migration, Edge, Cron ou benchmark executado.
HUMAN_CHECKPOINT: APROVAR PUBLICAÇÃO MANUAL DO RELÓGIO NA MAIN.

## 2026-10-20 — GITHUB_CLOCK_MANUAL_VALIDATION_PREPARATION (GREEN offline)

Decisão humana registrada: alternativa B como candidata principal, apenas
arquitetura. Host DESKTOP-VU6VMS6, sheets-supabase-sync, dev/HEAD
b84f1b2eeca0f9ffe3fa135ba03f2468eb3928e9; origin/dev igual por ls-remote;
main 88ae3008140905ce05a4fcf7c01bc6db72db6c78. Preservadas as cinco mudanças
locais da etapa anterior. Nenhum Git de escrita.

GETs de governança reconfirmaram main padrão/default token read e staging com
uma única regra branch dev, sete secrets por nomes, nenhuma repository variable.
Lista paginada de workflows contém apenas CI e executor manual; arquivos main/dev
inspecionados, sem schedule ou relógio equivalente. Escopo não comprova ausência
de acionadores externos. Credenciais/valores de secrets não lidos, nenhum objeto
remoto alterado. Executor blob idêntico e sem mudança; gates GREEN não repetidos.

V2 lido integralmente e preservado; candidato manual novo recusa schedule e
workflow path alternativo, vincula autorização ao run_number exato/attempt 1,
mantém alvo fixo dev e um POST sem retry, registra tentativa antes da chamada,
HTTP/IDs/SHA/horários sanitizados. contents:read justificado pelo GET da revisão
dev; actions:write explicitamente amplo no domínio Actions. Environment restringe
branch, não arquivo de workflow. Token emitido/handoff real permanecem pendentes.

Helper offline novo classifica resumo/metadados allowlisted: sources_failed>0
em processo/GitHub bem-sucedido produz SOURCES_FAILED; ausência de guard ou
reconciliação impede GREEN. Não lê logs/rede/DB nem altera executor. API oficial
2026-03-10 documenta HTTP 200 com run ID; return_run_details avaliado, não listado
no contrato atual, não enviado. Resposta ambígua exige inspeção, nunca replay.

150 testes offline PASS: 50 manual + 27 observação + 32 v1 + 34 v2 + 7 dispatcher.
PyYAML 6.0.3 já instalado no Python de sistema validou sintaxe/estrutura do YAML;
nenhuma dependência instalada, Python/executor de produção sem mudanças.
Documentados planos A publicação manual inerte, B teste único com outra aprovação,
C observação/reconciliação staging, D schedule após decisão própria sem frequência.
Rollback preserva executor/secrets e acompanha filhos já aceitos.

Nenhum workflow publicado/disparado, schedule, secret, token, environment, SQL,
produção, extensão, Edge, Cron, migration, benchmark, commit ou push executado.
[Plano, evidências e relatório](../drafts/github_scheduler/MANUAL_VALIDATION.md).
Próximo gate GITHUB_CLOCK_MANUAL_PUBLICATION; aguardar
APROVAR PUBLICAÇÃO MANUAL DO RELÓGIO NA MAIN, sem autorizar dispatch real.

## 2026-10-20 — SCHEDULER_ARCHITECTURE_DECISION (revisão offline, YELLOW)

Host DESKTOP-VU6VMS6, raiz sheets-supabase-sync, dev no HEAD
b84f1b2eeca0f9ffe3fa135ba03f2468eb3928e9, worktree inicialmente limpa.
Origin/dev confirmado por ls-remote no mesmo SHA, main no
88ae3008140905ce05a4fcf7c01bc6db72db6c78. Nenhum Git de escrita.
Regras e documentos de contexto lidos; objetivo explícito deste gate usado.

GETs GitHub confirmaram main padrão, público, Actions habilitado, default token
read; executor ativo com mesmo blob local/main/dev. Run 39247320871 permanece
completed/success/dev/attempt 1, apenas metadados consultados, sem repetir.
Staging tem única política branch dev e sete secrets, conferidas só por nomes;
repository secrets/variables vazias. Valores de secrets não consultados.
Gates remote runner e probe transacional continuam GREEN; redesign Cron YELLOW.

Documentação oficial atual reconferida. B viável com actions:write explícito no
job, token automático, sem PAT. Novo draft v2 preserva integralmente o anterior
e envia apenas ref dev conforme contrato atual HTTP 200/run_id; nenhum schedule.
Tratados limites: environment restringe branch, não arquivo exclusivo de workflow;
actions:write amplo, race em dev, perda de tick, inatividade e resposta ambígua.
Dispatcher pode retornar zero com sources_failed>0: monitor deve ler resumo,
não apenas verde do GitHub. Nenhum Python/executor/guard alterado.

Testes offline: 34/34 v2, 32/32 históricos e 7/7 dispatcher PASS. Fetch e
dependências operacionais simulados, nenhuma chamada Google/DB pelos testes.
Nenhuma validação de token emitido ou execução hospedada alegada. Sem parser
YAML/dependência instalada; validação hospedada fica para gate humano próprio.

Criados draft v2, testes v2 e ADR comparativa; índice de decisões atualizado.
Rascunhos Cron/Edge/probe e todos os documentos anteriores preservados.
Sem alteração .github/workflows, schedule, dispatch, secret/environment, SQL,
Cron, extensão, Edge deploy, produção, Migration 5, benchmark, commit ou push.
[ADR e resultado obrigatório](decisions/20261020_supabase_cron_vs_github_actions_schedule.md).
Próximo gate proposto: GITHUB_CLOCK_MANUAL_VALIDATION_PREPARATION, após decisão
humana sobre B; publicação/teste real e recorrência continuam sem autorização.

## 2026-10-19 — SCHEDULER_ARCHITECTURE_DECISION (proposta, YELLOW para ativação)

Preflight Git: raiz sheets-supabase-sync, dev em
00a06ecc8e3fb758351d4a14e6c991a6dd370b14, inicialmente sem alterações locais.
Regras/contexto do repositório e workflow atual lidos. Gates remoto e probe
transacional mantidos GREEN, sem repetição; baseline 9/11/8 somente contextual,
sem conexão ao Supabase. Rascunhos Cron/Edge e evidências preservados intactos.

Consultas GitHub exclusivamente GET via gh api: repo público não arquivado,
default_branch=main, Actions habilitado, allowed_actions=all e pinning obrigatório
false. Default_workflow_permissions=read; aprovação de PR por token=false.
staging-dispatch ativo, ID 388468858; scheduled-sync.yml presente em main/dev
e igual ao arquivo local, blob 65d16e28a9e00918a0eac2213ab57b0e73fc6ea0.
Environment staging: custom_branch_policies=true, uma única regra branch dev,
sem regra de tags. Sete secrets verificadas apenas por nomes, sem valores:
APP_ENV, SUPABASE_PROJECT_REF, SUPABASE_ALLOWED_PROJECT_REF, SUPABASE_URL,
SUPABASE_DB_URL, GOOGLE_SERVICE_ACCOUNT_JSON, STAGING_SYNC_CONFIG_JSON.
Nenhuma variável de repositório cadastrada atualmente.

Alternativas comparadas na ADR proposta e drafts/github_scheduler/README.md.
Recomendação B: relógio separado em main, GITHUB_TOKEN automático restrito ao
job com actions:write/contents:read, dispatch fixo scheduled-sync.yml ref dev,
worker Python existente/environment staging. Destino mantém contents:read e
não foi modificado; não requer Actions:write para executar o dispatcher.
Documentação oficial confirma dispatch interno com GITHUB_TOKEN e exceção à
supressão de novos eventos; defaults read podem ser ajustados declarativamente
pelo job. Token efetivamente emitido e handoff real ainda precisam de teste
autorizado futuro; não confundir permissões da CLI local com as do job futuro.

YAML preparado somente drafts/github_scheduler/staging-clock.draft.yml. Sem
schedule/expressão cron, checkout, action terceira, environment ou secrets de
Supabase/Google. Apenas token automático; opt-in STAGING_CLOCK_ENABLED inexistente
hoje falha fechado. Manual de teste exige confirmação, SHA e expiry até 15 min;
essa janela não é frequência de cliente. Repo/main/event/run_attempt validados;
destino ativo/revisão e runs concorrentes consultados antes de um único POST.
Redirects bloqueados, timeout, sem retries ou fallback PAT. Retorno run_id/URLs
e GET do filho conferem workflow/event/dev/SHA/attempt. Resultado do relógio
significa dispatch aceito, não Python ou reconciliação concluídos.

Riscos registrados: schedule main-only sujeito a atrasos/perdas e desativação
em repo público após 60 dias sem atividade; sem SLA de horário. Menor intervalo
técnico documentado de cinco minutos não foi escolhido como frequência.
Destino atual mantém um ativo/um pendente por grupo; nova chegada pode substituir
pendente. Preflight não evita corrida manual/automático. Concurrency não deduplica,
reruns/new runs e ambiguidade não autorizam replay automático. Ref dev móvel
exige congelamento no teste; conferência após POST não previne execução com SHA
divergente. Correlação após resposta perdida pode ser inconclusiva sem inputs
novos no destino, que não foram adicionados neste gate.

Custos: runner padrão de repo público com execução gratuita documentada, sem
prometer custo total zero, planos/quotas imutáveis. B reduz componentes/credenciais;
A tem consumo adicional DB/Edge/egress e manutenção, sem nova consulta de cobrança.
Ambas dependem do worker staging disponível. Frequência/SLA/timezone/volume/
backlog/monitoramento ainda dependem dos clientes; recorrência não autorizada.

32 testes Node offline aprovados, executando o JavaScript extraído do YAML real
com fetch/process/clock/log mockados. Cobertura: payload fixo, contexto/fork/ref,
rerun/enable/confirmação/janela/SHA, busy/paginação, rede/timeout/redirect/erros/
204/200 ambíguo, observação e vínculo do run, ausência de secrets nos logs.
Nenhuma chamada de API foi feita pelos testes. Não comprovam token emitido,
validação de workflow hospedado ou execução schedule; nenhuma dependência nova.

ADR docs/decisions/20261019_scheduler_architecture_decision.md permanece PROPOSTA.
Planos de ativação separada e rollback estão no pacote: publicar manual-only
desabilitado após aprovação, autorizar um teste novo em gate distinto, observar
parent/child e reconciliar staging; recorrência somente depois de requisitos.
Rollback desabilita só clock/opt-in, preserva destino manual e secrets e não
reenvia dispatch ambíguo nem desfaz sync em andamento.

Nenhum arquivo .github/workflows, código Python, SQL, objeto remoto, secret,
PAT, extensão, Edge, Cron, schedule ativo, workflow_dispatch, sync, produção,
Migration 5, benchmark, commit ou push alterado/executado. Supabase Cron não
foi abandonado oficialmente. Próxima aprovação: APROVAR ADR PROPOSTA DE RELÓGIO
GITHUB ACTIONS, sem publicação, teste ou recorrência implícitos.

Verificação documental e git diff --check aprovados (apenas aviso LF/CRLF).
Scan sanitizado de três arquivos novos do pacote/teste: zero assinaturas de
credenciais. Valores de autenticação dos mocks são artificiais. Diff confirmou
nenhuma alteração em .github/workflows, src ou drafts/cron_controlled_dispatch.

## 2026-10-19 — CRON_EDGE_AUTHORIZATION_REDESIGN (YELLOW, somente offline)

Repositório sheets-supabase-sync, branch dev. HEAD inicial 7c3649c; na verificação
final passou a 772d43e755f9c6755e704520f4b6410989e85e35 por operação externa a esta
execução. Nenhum comando Git de escrita foi executado pelo agente. Registros,
rascunhos e evidência do probe anterior preservados; não repetir gates concluídos.
automation_remote_runner_validated e probe transacional continuam GREEN.
Baseline 9/11/8 usado apenas como contexto, sem nova conexão ao staging.

Decisão humana adicional, obtida por esclarecimento de política: EXIGIR PROVA
DA ORIGEM CRON, mesmo quando a chamada falsa ocorra depois de uma liberação
válida. Não se aceitou que um UUID público e o estado released autorizem o
chamador HTTP. Wake-only para iniciar dispatch foi rejeitado; header X-Cron,
IP compartilhado, bearer permanente, nonce copiado da fila e integridade de
uma mensagem sem resistência à corrida de replay não satisfazem o requisito.
Referências oficiais de visibilidade/default grants pg_net foram reconsultadas.

Pacote corrente preparado em drafts/cron_controlled_dispatch/redesign/:
- edge/dispatch.mjs: wake público sem ledger/transport/PAT, retorna 403; handler
  de dispatch exige verificador independente antes da claim. Grant vinculado
  a UUID/release/repo/workflow/dev/SHA/janela curta; sem autenticação baseada em
  bearer global, header declarado pelo cliente ou conhecimento do identificador.
- edge/ledger.mjs: adapter de identidade PostgreSQL dedicada, somente três SQLs
  fixos parametrizados, conexão/transação independente por chamada, COMMIT
  confirmado antes do retorno e confirmação READ ONLY. Sem service_role,
  PostgREST público, retries, logs ou detalhes de erros do driver.
- sql/10_control.draft.sql e 20_routines.draft.sql: schema privado novo, owner
  NOLOGIN/NOBYPASSRLS sem privilégios amplos, capacidade Edge NOLOGIN com USAGE
  e somente EXECUTE de claim/confirm/finish. Release/cancel só operador, tabela
  inacessível diretamente à Edge, trigger/invariantes contra rearme. Sem xids
  como prova de commit. Instalação nova, não alteração do probe ou das migrations.
- sql/30_audit_readonly.sql: catálogo de owners/roles/ACL/EXECUTE/schemas, não
  executado. SQLs mutáveis abortam incondicionalmente antes de DDL.

Repo DungeonCodes/sheets-supabase-sync, workflow scheduled-sync.yml e ref dev
fixos. GitHub fetch com timeout 15s, redirect:error e sem retry. HTTP 200 só é
accepted com run_id/URLs correspondentes; 204, timeout, falha de rede ou corpo
inválido são ambíguos. Auditoria guarda somente status/contadores/IDs sanitizados;
falha de auditoria não autoriza novo envio. PAT futuro só no secret store Edge,
granular Actions:write/repo único/validade limitada; nenhuma credencial criada.

Bloqueio explícito: verificador real da origem Cron NÃO implementado/provisionado.
Mocks de verificação não provam identidade. Nenhuma identidade nativa pg_net foi
presumida. Driver vivo, identidade LOGIN dedicada, TLS/binding staging e grants
PUBLIC herdados exigem revisão futura; um LOGIN novo pode acessar net por PUBLIC.
Não há enqueue/job/ativação v2 porque ligá-los a wake-only violaria a decisão.
Entrypoints antigo e novo abortam; removido wiring antigo de service_role e
bearer reutilizável. Handler/RPC antigos mantidos como fixtures rejeitadas dos
testes históricos, sem importação operacional. A cadeia completa não está pronta.

Exceção de leitores administrativos do probe sintético não foi estendida a
segredos, capabilities ou dados reais de autorização. Ledger novo não contém
campos de token, senha, DSN, chave, corpo HTTP ou dados pessoais. Owner restrito
e REVOKE não isolam a plataforma/superusuário/read-all; classificação dos metadados
reais e identidade de ingresso precisam revisão antes de implantação.

Testes offline: 68 Node aprovados (33 novos + 35 anteriores), oito contratos
Python aprovados; Deno check --no-remote --no-config dos dois entrypoints passou.
Testes cobrem falso/antecipado/expirado, binding incorreto, ausência de verificador,
replay, 32 concorrentes, ausência de rearme, commit incerto, rede/timeout/redirect,
200 inválido/204, auditoria falha, SQL parametrizado e ausência de logs/leaks.
Casos anteriores preservados; verificações do entrypoint foram fortalecidas para
exigir ausência de env/listener amplo. Não foi repetida a suíte extensa de 241
testes nem qualquer gate remoto. SQL novo tem contratos textuais, não validação
em servidor; o modelo ledger e os mocks não substituem prova da integração.

ADR específica criada, índice de decisões e README atualizados. Nenhum SQL,
extensão, Edge, token/PAT, Vault, GitHub Secret, Cron/job, workflow_dispatch,
sincronização, Migration 5, produção, benchmark, commit ou push. Próxima aprovação:
APROVAR REVISÃO DA FRONTEIRA DE INGRESSO COM PROVA DE ORIGEM CRON. Não é aprovação
de implantação; manter travas até mecanismo concreto revisado. Risco MEDIUM do
desenho ainda incompleto, sem impacto operacional neste gate.

Verificador documental e git diff --check aprovados (avisos apenas LF/CRLF).
Scan local sanitizado dos oito arquivos novos de pacote/teste: zero assinaturas
de credenciais; valores usados nos mocks são artificiais. Scanner por padrões
não constitui prova absoluta de ausência de segredo.

## 2026-10-19 — CRON_STAGING_TRANSACTIONAL_PROBE_RESUME (GREEN somente transacional)

Autorização humana específica: retomar o probe aceitando exclusivamente leitura
dos estados sintéticos pelos papéis administrativos internos do Supabase.
Exceção NÃO abrange tokens, credenciais, dados operacionais nem desenho futuro.
Repositório sheets-supabase-sync, branch dev, HEAD
7c3649cf676f2aee010a7a1156f2aee7a91616cf; alterações locais anteriores preservadas.
Runbook e quatro SQLs do probe revistos, sem mudar o SQL aprovado. Nenhum script
de setup/armamento do pacote Cron foi utilizado; suas travas permanecem intactas.

Preflight READ ONLY em 14:12:39 UTC: staging guard existente aprovado, usuário
postgres/banco postgres, CREATE no banco e USAGE em plpgsql presentes, schema
cron_tx_probe ausente. Atributos efetivos: supabase_read_only_user e
supabase_etl_admin têm LOGIN=true, SUPERUSER=false, BYPASSRLS=true e herança
pg_read_all_data=true. Acesso de leitura desses papéis foi aceito apenas para
este conteúdo sintético. Nenhum atributo, membership ou privilégio global mudou.
service_role também tem BYPASSRLS, porém sem acesso efetivo ao schema/tabelas
ou EXECUTE do probe após instalação; BYPASSRLS não substitui privilégios SQL.

Execução supervisionada única em 14:14:04–14:14:11 UTC (11:14 BRT), com três
conexões persistentes independentes: A=109087, B=109098, C=109099. Evidência local:
drafts/cron_controlled_dispatch/probe/execution_20261019_sanitized.json.
Baseline READ ONLY imediatamente anterior: sync_runs=9, raw_import_rows=11,
raw_current_rows=8. O setup aprovado foi executado uma vez, transacionalmente.

Objetos criados somente no schema cron_tx_probe, owner postgres: control e
permits (duas tabelas), claim(text) e no_rearm() (duas funções SECURITY INVOKER,
search_path=pg_catalog), trigger no_rearm e índices implícitos de duas PKs.
São quatro linhas: um controle e casos rollback/race/expired. Conteúdo apenas
sintético: nomes de casos, ref dev, estados 0/1, timestamps e PIDs; não há
tokens, passwords, URLs, connection strings, identificadores de autorização real,
dados de alunos/clientes ou referências a fontes. Nenhuma dependência HTTP.

Ownership, ACLs e funções verificados antes das claims. PUBLIC sem EXECUTE;
anon/authenticated/service_role sem USAGE, SELECT/UPDATE ou EXECUTE; demais
LOGIN não administrativos sem alteração/EXECUTE. Os dois leitores internos
autorizados têm USAGE/SELECT, mas UPDATE=false e claim EXECUTE=false.
postgres e o superusuário gerenciado supabase_admin permanecem privilegiados;
não se afirma isolamento contra o administrador da plataforma.

Resultados reais PostgreSQL, sem mocks:

- Claim rollback em A retornou true dentro de transação; C viu contador zero.
- SELECT 1/0 injetou falha deliberada SQLSTATE 22012 antes da confirmação;
  ROLLBACK em A; C confirmou contador zero, sem consumo persistente.
- B consumiu rollback e fez COMMIT; C viu contador um, claimant de outro backend.
- Replay do caso confirmado retornou false, sem reset ou novo consumo.
- A consumiu race sem confirmar; B tentou simultaneamente. C comprovou
  A=ANY(pg_blocking_pids(B))=true e ainda viu race=0, sem ler texto de queries.
- Após COMMIT de A, B retornou false e confirmou sua transação sem consumir.
  C viu race=1. Houve exatamente um vencedor confirmado entre os concorrentes.
- Replay de race, caso expired e caso inexistente retornaram false.
- Verificador final: exactly_three_cases/two_consumed/expired_unused/
  bounded_claims/no_definer_functions todos true. Sem pg_xact_status/claim_xid.

Encerramento: 30_disable.draft.sql executado uma vez, com disabled=true;
nova tentativa autorizada de claim após desativação retornou false. Estado
preservado: rollback=1, race=1, expired=0; control.enabled=false. Nenhum DROP,
DELETE, reset de autorização ou remoção de evidência. Todas as conexões fechadas.
Inspeção READ ONLY adicional de todos os papéis confirmou EXECUTE nas duas
funções apenas para postgres e supabase_admin; desativação reconfirmada.
Objetos/índices e quatro linhas sintéticas permanecem para auditoria; nenhuma
rotina executada em background e nenhum job criado.

Reconciliação efetivamente medida após desativação: sync_runs=9,
raw_import_rows=11, raw_current_rows=8; deltas operacionais 0/0/0.
Lista/versões de extensões idênticas antes/depois. Toda escrita executada
foi limitada ao schema sintético; tabelas operacionais receberam somente as
consultas de contagem em READ ONLY. Não houve requisição HTTP, fonte Google,
API GitHub/Supabase Management, uso de Cron/net/Vault, produção, Edge, PAT,
secret, workflow_dispatch, sincronização, Migration 5, benchmark, commit ou push.
Somente a autenticação PostgreSQL já autorizada foi usada; nenhum valor de
credencial foi registrado nem colocado nos objetos/evidências.

Limites: GREEN valida apenas atomicidade, visibilidade, bloqueio concorrente,
rollback, expiração e replay observados neste modelo reduzido. Não valida
PostgREST, comportamento de Cron/Edge/HTTP, isolamento de secrets, exactly-once,
durabilidade após restore/failover ou o sistema completo. Leitores privilegiados
e superusuário continuam parte explícita da fronteira de confiança. O pacote
Cron permanece YELLOW; automation_remote_runner_validated permanece GREEN.
Risco do probe encerrado LOW. Próximo gate: CRON_EDGE_AUTHORIZATION_REDESIGN,
não iniciado. Nenhuma nova execução autorizada por este resultado.

## 2026-10-19 — CRON_STAGING_TRANSACTIONAL_PROBE: preflight bloqueado (YELLOW)

Autorização humana específica recebida: APROVAR PROBE TRANSACIONAL ISOLADO EM
STAGING. Raiz sheets-supabase-sync, branch dev, HEAD
7c3649cf676f2aee010a7a1156f2aee7a91616cf. Alterações locais anteriores
preservadas. Runbook, revisão de segurança e quatro SQLs do probe lidos
integralmente; nenhum SQL do pacote operacional foi selecionado para execução.

Preflight real em 19/10/2026, 14:05:34–14:05:35 UTC (11:05 BRT), pela conexão
PostgreSQL staging existente, validada por validate_staging_access com destino
e project ref permitidos. Não houve autenticação Management API. Três conexões
simultâneas verificadas em READ ONLY: backends 108394, 108397 e 108398, usuário
postgres, banco postgres, permissões CREATE no banco e USAGE de plpgsql presentes.
cron_tx_probe ausente nas três conexões. Nenhum conflito de objeto encontrado.
Baseline READ ONLY: sync_runs=9, raw_import_rows=11, raw_current_rows=8.
Catálogo de extensões: pg_stat_statements 1.11, pgcrypto 1.3, plpgsql 1.0,
supabase_vault 0.3.1 e uuid-ossp 1.1. Somente metadados do catálogo foram lidos;
nenhum objeto ou segredo Vault consultado, nenhuma extensão instalada.

Auditoria adicional READ ONLY dos atributos/memberships efetivos encontrou
supabase_read_only_user e supabase_etl_admin com LOGIN e USAGE efetivo de
pg_read_all_data. Ambos não são superuser nem herdam postgres, segundo a
consulta. Não se presumiu que sejam papéis administrativos autorizados pelo
limite de confiança do runbook. Demais papéis cliente anon/authenticated/
service_role não apresentaram essa herança.

Bloqueio: o runbook exige parar se houver acesso não administrativo ao
schema/tabelas/função. pg_read_all_data concede SELECT geral e USAGE em schemas,
mesmo sem grants explícitos; o setup aprovado não habilita RLS. Portanto, suas
revogações locais não demonstrariam a fronteira de leitura exigida. Trata-se
de conclusão sobre privilégios herdados documentados, não de um teste de
exposição sobre tabelas criadas (nenhuma foi criada). Referência oficial:
https://www.postgresql.org/docs/current/predefined-roles.html

Preflight completo: BLOCKED. Conforme a ordem de parar quando qualquer condição
falhar, nenhuma instalação ou escrita SQL foi iniciada. Cenários A–G,
concorrência, visibilidade de commit, replay e expiração NÃO executados.
Baseline posterior não coletado após a interrupção; não alegar reconciliação
antes/depois nem deltas medidos. Todos os comandos remotos executados foram
transações READ ONLY e consultas de metadados/contagens. Conexões encerradas.

Objetos criados: zero. Objetos do probe remanescentes: zero. Desativação e
rollback lógico não necessários nem executados, pois não houve instalação.
Nenhuma função SECURITY DEFINER, extensão, job, recorrência, Edge, PAT, secret,
workflow_dispatch, sincronização, Migration 5, benchmark, commit ou push.
Não houve acesso a produção, API GitHub, fontes Google ou valores Vault.
Somente a credencial de conexão PostgreSQL já autorizada foi usada; nenhum
valor de credencial, connection string, chave ou dado privado foi registrado.

automation_remote_runner_validated permanece GREEN; pacote Cron permanece
YELLOW. Risco operacional deste gate LOW, sem escrita. Próximo gate recomendado:
CRON_PROBE_PRIVILEGE_BOUNDARY_REVIEW. Revisar humanamente a classificação dos
papéis administrativos confiáveis ou preparar proteção local adicional para
nova revisão; não revogar memberships nem mudar privilégios globais. Esta
autorização não permite alterar o desenho para contornar a condição de parada.
Nenhum próximo gate iniciado automaticamente.

## 2026-10-19 — CRON_STAGING_INACTIVE_PREPARATION_REVIEW (YELLOW)

Raiz Git confirmada, dev em 7c3649cf676f2aee010a7a1156f2aee7a91616cf.
Alterações documentais e rascunhos locais anteriores preservados. Nenhum fetch,
commit, push ou acesso operacional remoto. automation_remote_runner_validated
permanece GREEN, run 39247320871, sem repetir teste; baseline 9/11/8 é apenas
contexto anterior, não nova medição. Segurança anterior permanece MITIGATED.

README, oito SQLs, três arquivos Edge, testes Node/Python, fragmento workflow,
ADR e registros atuais auditados. Revisão em drafts/cron_controlled_dispatch/REVIEW.md.
Documentação oficial atual confirma que REVOKE net por postgres pode não remover
grants de supabase_admin e que restrição de ACL/RLS por projeto não é suportada.
Não aceitar segredo reutilizável na fila como isolado; papéis LOGIN podem ler e
alterar fila. A chave ampla service_role no adapter não é mínimo privilégio.
Capability por autorização/janela/operação e identidade restrita foram propostas,
mas não implementadas/provisionadas. A integração completa continua bloqueada.

Cinco scripts operacionais 10/20/30/40/50 receberam abort explícito inicial;
entrypoint Edge também bloqueado antes de env/serve. Implementações anteriores
mantidas para revisão, rollback 70 preservado, nenhum script aplicado. Novo
inventário READ ONLY cobre LOGIN, memberships, owners, EXECUTE, Vault/net e
schemas expostos; não executado. Ausência de configuração visível não prova
ausência de exposição Data API; exige conferência humana futura.

Probe novo em drafts/cron_controlled_dispatch/probe: schema cron_tx_probe,
duas tabelas (quatro linhas sintéticas), duas funções SECURITY INVOKER, trigger,
três conexões independentes, guardas, timeouts, observação e rollback lógico.
Sem extensões, jobs, HTTP, credenciais, Edge ou tabelas do sincronizador.
Runbook manual comprovará visibilidade antes/depois de commit e rollback,
bloqueio concorrente, único vencedor, expiração e replay; nenhum probe executado.
pg_xact_status não é fonte de atomicidade nem necessário sob observação
independente comprovada; a implementação operacional ainda precisa de revisão.

Testes offline direcionados: 35 Node aprovados (27 mocks anteriores + oito
contratos de revisão/probe), oito contratos Python aprovados. Nomes de dois
testes Python corrigidos para não sugerir comprovação de privilégios/commit
operacionais. Nenhuma suíte extensa, integração ou benchmark repetido. Mocks e
contratos textuais não provam sintaxe/semântica SQL ou segurança implantada.

Nenhum SQL/extensão/job/deploy/token/secret/dispatch/migration/produção/recorrência.
As sete GitHub Secrets não foram acessadas nem alteradas. Próxima aprovação
somente APROVAR PROBE TRANSACIONAL ISOLADO EM STAGING. Risco MEDIUM para a
integração pendente; prova de banco ainda não realizada.

Deno check --no-remote --no-config e verificador documental aprovados; git diff
--check sem erro (apenas aviso de normalização LF/CRLF do run_log). Scan local
sanitizado em 23 arquivos de artefatos/testes: zero assinaturas de credenciais
após distinguir um falso positivo em identificador de método de teste. Revisão
manual encontrou apenas valores artificiais de mocks, não credenciais reais.
Scanner por padrões não prova ausência absoluta de segredo. Nenhum valor ou
fragmento confidencial foi mostrado. Resultados de testes direcionados
reconfirmados após ajustes finais; a suíte extensa anterior não foi repetida.

## 2026-10-19 — CRON_CONTROLLED_DISPATCH_SQL_PREPARATION (YELLOW)

Repositório descoberto por git rev-parse, dev em 7c3649c. As alterações
pré-existentes em run_log.md e a proposta documental ainda não versionada foram
preservadas. automation_remote_runner_validated continua GREEN, run 39247320871;
nenhuma repetição ou reabertura do teste remoto. Baseline de contexto: 9/11/8,
sem nova consulta ao banco ou chamada operacional externa neste gate.

Revisão crítica com fontes primárias: CALL top-level no caminho libpq do
pg_cron 1.6.4 permite COMMIT real sob as restrições PostgreSQL. Porém http 1.6
força redirects e não permite desligá-los pelas curlopts expostas; pg_net direto
não garante envio único sob falha do worker e colocaria PAT GitHub na fila.
A recomendação foi corrigida e registrada na revisão vigente da ADR, mantendo
o diagnóstico anterior como histórico.

Arquitetura proposta: pg_cron -> pg_net -> Edge Function mínima -> GitHub.
GitHub PAT somente no secret store Edge; Vault guarda apenas credencial distinta
para o gatilho. pg_net terá ACLs restritas antes de qualquer segredo; formatos
impedem confundir PAT com credencial do gatilho. Revisão dos privilégios usa
como evidência a auditoria READ ONLY anterior (service_role podia ler Vault),
e prepara consultas novas de metadados, sem executá-las neste gate.

Autorização única: claim com lock em RPC normal, synchronous_commit=on;
segunda RPC verifica pg_xact_status(claim_xid)=committed antes do único POST
GitHub. Não há COMMIT interno numa função SECURITY DEFINER. Não há retry de
claim, confirmação, HTTP ou auditoria; timeout/ambiguidade não rearmam permissão.
São aceitas perda do envio e necessidade de investigação, sem afirmar
exactly-once. Headers e corpos de erro não são registrados. O retorno 200 com
workflow_run_id/URLs é correlacionado, mas ainda exige observar dispatcher e
reconciliar staging para comprovar sucesso ponta a ponta.

Pacote preparado em drafts/cron_controlled_dispatch: oito SQLs separados para
inspeção, extensões, ACL/controle privado, rotinas, configuração INATIVA,
armamento com aprovação distinta, validação READ ONLY e rollback sem DELETE ou
DROP. Inclui handler/adapters Edge sem dependências npm e fragmento de workflow
para UUID, ref dev, SHA aprovado e bloqueio de rerun. O workflow real e o
sincronizador Python não foram modificados. Não foi alterada Migration 5,
Analytics ou qualquer migration aplicada.

Testes offline: 27 testes Node passaram com mocks HTTP/GitHub e ledger de
política, incluindo 32 entregas concorrentes/replay, expiração, consumo prévio,
commit não confirmado, falha após commit, timeout, erros, 200 inválido/204,
branch incorreta, troca de categorias de credencial e ausência de leaks.
O handler e os adapters testados são os mesmos arquivos do rascunho.

Python: 196 testes unitários (incluindo oito contratos estáticos novos), dois
de segurança, dois de contrato, 25 de test_sync e 16 de instituição isolada
passaram: 241 aprovados. Um teste end-to-end dependente de integração foi
pulado. Os oito contratos dos SQLs foram reexecutados após a última etapa e
passaram. Nenhuma suíte de performance/benchmark ou integração remota executada.
Deno check --no-remote --no-config passou; verificador documental passou.

Limites: nenhum SQL foi aplicado, nem mesmo localmente. Não houve parser ou
servidor PostgreSQL validando sintaxe/semântica dos scripts. Docker não estava
acessível; mocks não comprovam ACL/atomicidade implantadas. Há probe de commit
RPC sem GitHub preparado para revisão futura, não executado. Deno check é
verificação estática, não execução hospedada Supabase. Risco MEDIUM; status
YELLOW até revisão humana, isolamento, implantação e prova autorizada.

Nenhuma extensão instalada, job Cron criado/ativado, PAT/segredo criado,
Vault gravado, workflow disparado, produção acessada, benchmark iniciado,
commit ou push feito. As sete GitHub Secrets permanecem intactas. Próxima
aprovação: revisão dos arquivos e preparação INATIVA/isolamento e probe sem
dispatch; criar credenciais e armar um único teste exigem autorizações distintas.

## 2026-10-19 — SUPABASE_CRON_SINGLE_CONTROLLED_DISPATCH: diagnóstico (YELLOW)

Repositório descoberto por git rev-parse; dev local e remota em
7c3649cf676f2aee010a7a1156f2aee7a91616cf, worktree inicialmente limpa. Desde o
SHA do gate remoto, somente run_log.md mudou. automation_remote_runner_validated
permanece concluído: run 39247320871 consultada apenas por metadados, success.
Não houve repetição do teste remoto nem investigação dos tokens revogados.

Inspeção PostgreSQL staging READ ONLY em 2026-10-19T12:26:12.384503+00:00:
pg_cron 1.6.4 e pg_net 0.20.4 disponíveis, não instalados; catálogos cron/net
inexistentes, sem jobs pg_cron neste banco. Vault 0.3.1 instalado, zero secrets.
service_role tem acesso efetivo à view de segredos descriptografados; revisar
ACLs antes de inserir PAT GitHub. anon/authenticated não possuem esse acesso.
Papel atual postgres não é superuser; instalação exige caminho administrativo
suportado e revisão humana. Nenhuma extensão foi criada ou habilitada.

Baseline preservado: sync_runs=9, raw_import_rows=11, raw_current_rows=8.
Seleção somente leitura: uma demo, sources_due=0, sources_failed=0, skipped=1.
Intervalo 180 minutos; próxima elegibilidade natural prevista para
2026-10-19T14:48:49.361510+00:00, salvo execução posterior. Não forçar due.

Proposta registrada em docs/decisions/20261019_cron_single_controlled_dispatch_design.md.
PAT GitHub granular, repo único, Actions: write, validade curta, criação humana
e Vault após isolamento; sete GitHub Secrets preservadas. API workflow_dispatch
com ref dev e return_run_details permite correlacionar run_id, sem considerar
HTTP 200 como conclusão do Python.

pg_net permite limitar enfileiramento, mas seu worker faz HTTP antes do COMMIT
do consumo da fila: risco de repetição após falha inferido do código oficial,
sem teste de falha no ambiente. Recomendação proposta: procedimento Cron com
consumo durável da autorização e desativação do job antes de HTTP síncrono.
Extensão http 1.6 disponível e não instalada; cron.use_background_workers=off.
Controle transacional/top-level CALL precisa de revisão antes de implantação.
Nenhuma chamada manual HTTP será aceita como prova de execução Cron.

Free: recursos/egress/pausa e recomendação de até oito jobs concorrentes
registrados no desenho, com fontes oficiais; plano de faturamento não foi
reconsultado via Management API. GitHub repo público, runner padrão gratuito.
Sem upgrade, contratação ou nova plataforma paga proposta.

Resultado YELLOW: faltam aprovação do desenho, revisão SQL/ACL, instalação
administrativa e credencial futura. Próxima aprovação: desenho com HTTP
síncrono e preparação do SQL para revisão humana, sem aplicar, criar segredo,
criar job ou disparar. Nenhum Cron, recorrência, token, workflow, migration,
sincronizador, produção, benchmark, commit ou push foi criado/alterado/executado.
Somente documentação local alterada; registros anteriores preservados.

## 2026-10-19 — AUTOMATION_REMOTE_RUNNER_EXECUTION (GREEN)

Classificação: automation_remote_runner_validated. O usuário autorizou
explicitamente UMA execução manual staging neste gate. Segurança permanece
MITIGATED: os dois tokens Legacy foram revogados pelo usuário; nenhum PAT
revogado foi utilizado, nenhum token foi criado e nenhuma chamada à Management
API Supabase foi feita. Sem evidência de exposição das sete GitHub Secrets.

Revalidação imediata: repositório DungeonCodes/sheets-supabase-sync, branch dev,
HEAD local e remoto 1e0d21831bfba3f6b98b1d7598272988ef372cac. Workflow
staging-dispatch ativo, exclusivamente manual e idêntico ao arquivo local.
Environment staging com uma única política de branch dev, sem política de tags.
Os sete nomes de secrets foram conferidos, sem acesso a valores. Zero runs
anteriores desse workflow e nenhuma execução concorrente do repositório nos
estados consultados. A fonte de demonstração única, habilitada e ativa,
correspondeu integralmente à configuração operacional. Staging guard aprovado.
Dry-selection oficial: sources_total=1, sources_due=1, sources_failed=0,
sources_executed=0, sources_busy_deferred=0; nenhuma chamada Google local.

Baseline imediato em 2026-10-19T11:48:00.477637+00:00, via PostgreSQL staging
já autorizado: SELECT 1 passou, transação READ ONLY, TLS cliente ativo e zero
runs planned/running. Totais: sync_runs=8, raw_import_rows=11,
raw_current_rows=8. No escopo demo: duas runs, três eventos insert, três estados
atuais e zero tombstones; demais tipos de eventos zero.

Comando executado exatamente uma vez, sem retry:
gh workflow run scheduled-sync.yml --repo DungeonCodes/sheets-supabase-sync --ref dev

GitHub run_id=39247320871, run_attempt=1, event=workflow_dispatch, headBranch=dev,
headSha=1e0d21831bfba3f6b98b1d7598272988ef372cac, conclusion=success.
URL: https://github.com/DungeonCodes/sheets-supabase-sync/actions/runs/39247320871
Job dispatch=118042313121, GitHub-hosted runner (grupo GitHub Actions,
ubuntu-latest); deployment=7172925346, environment=staging, ref=dev e SHA
aprovado, confirmado pelas statuses de deployment vinculadas ao mesmo job.

Evidências do runner: checkout dev e SHA aprovado; Python 3.13.16 efetivo;
instalação do projeto/dependências concluída; materialização temporária,
staging guard, batch_cli/dispatcher e remoção de arquivos temporários passaram.
Os logs foram processados em memória, com saída restrita a campos permitidos,
sem imprimir ou persistir logs brutos nesta análise. O mascaramento do GitHub
substituiu também delimitadores JSON; contadores e status foram extraídos por
campos estritos e reconciliados independentemente no banco.

Resumo do dispatcher: sources_total=1, sources_due=1, sources_executed=1,
sources_failed=0, sources_busy_deferred=0, sources_no_changes=1,
sources_skipped=0; único status individual: demo autorizada -> no_changes.

Reconciliação em 2026-10-19T11:50:31.624321+00:00, somente PostgreSQL staging,
transação READ ONLY: sync_runs=9, raw_import_rows=11, raw_current_rows=8.
Deltas globais: +1, 0, 0. Exatamente uma nova run da demo, status applied,
iniciada e concluída em 2026-10-19T11:48:49.361510+00:00, com inserts=0,
updates=0, tombstones=0, restores=0 e unchanged=3. Nenhuma run nova de outra
fonte; zero planned/running. Estado da fonte: enabled=true,
lifecycle_status=active, consecutive_failures=0.

Totais da demo após execução: três runs, três eventos insert, três estados
atuais e zero tombstones. Deltas de eventos insert/update/tombstone/restore=0;
fingerprint agregado do estado (chaves/conteúdos já em hash, versões e flags
de exclusão) idêntico antes/depois. Efeitos compatíveis com no_changes: nova
run auditável, sem eventos raw nem alteração de estado. Nenhuma divergência
inesperada. Consulta final GitHub confirmou exatamente uma run, attempt=1.

Limites residuais já documentados: revogação não comprova ausência de uso
indevido passado; TLS ativo não comprova verificação de identidade do servidor.
Nenhuma política SSL/TLS foi alterada. Nenhuma produção acessada, recorrência
habilitada, migration aplicada, secret alterada, benchmark iniciado, código
Python modificado, commit ou push realizado. A única alteração local foi
adicionar este registro a docs/run_log.md, preservando entradas anteriores.

Próximo gate: SUPABASE_CRON_SINGLE_CONTROLLED_DISPATCH, NÃO iniciado.
Risco de prazo: LOW, sem bloqueio técnico observado para concluir este gate.
A autorização deste gate foi consumida; nova execução exige nova autorização.

## 2026-10-19 — revalidação do REMOTE_RUNNER_FINAL_PREFLIGHT (GREEN)

PRE_DISPATCH_SECURITY_TRIAGE: MITIGATED. O usuário confirmou a revogação manual
dos dois tokens Legacy no Dashboard. Não houve nova investigação dos tokens,
criação de PAT, autenticação Supabase ou uso da Management API. Não há evidência
de exposição das sete GitHub Secrets. Risco residual: a revogação não demonstra
ausência de uso indevido anterior nem elimina cópias históricas; não houve
rotação das credenciais sem relação demonstrada com o incidente.

Repositório descoberto por git rev-parse: branch dev, HEAD 1e0d218. Após fetch,
origin/dev...HEAD = 0/0, também confirmado pela referência remota. A alteração
local pendente era somente docs/run_log.md, incluindo registro anterior de
preflight; todas as entradas existentes foram preservadas nesta revalidação.

GitHub: staging-dispatch ativo (scheduled-sync.yml), sem execuções registradas.
Workflow disponível em main e dev, com conteúdo idêntico ao arquivo local.
Environment staging usa custom_branch_policies e possui uma única regra:
branch dev, sem política de tags. Conferida somente a presença dos sete nomes:
APP_ENV, SUPABASE_PROJECT_REF, SUPABASE_ALLOWED_PROJECT_REF, SUPABASE_URL,
SUPABASE_DB_URL, GOOGLE_SERVICE_ACCOUNT_JSON e STAGING_SYNC_CONFIG_JSON.
Os valores das secrets não foram acessados.

Staging guard aprovado para leitura e para a validação de escrita confirmada;
a validação de escrita sem confirmação foi bloqueada, sem tentativa de escrita.
A configuração local contém somente a fonte de demonstração já autorizada,
habilitada e correspondente ao estado operacional. A configuração Google foi
validada localmente, sem chamadas de rede Google. Não houve acesso a produção.

Baseline anterior à seleção: 2026-10-19T11:17:47.075046+00:00. Baseline posterior:
2026-10-19T11:17:50.928658+00:00. SELECT 1 passou em transação READ ONLY,
transaction_read_only=on, conexão cliente com TLS ativo. Contadores globais:
sync_runs=8, raw_import_rows=11, raw_current_rows=8; runs planned/running=0.
No escopo da demonstração: uma fonte, duas runs, três eventos raw e três estados
atuais. Deltas globais zero contra 18/10 e contra o preflight já registrado em
19/10; deltas zero antes/depois do dry-select. Nenhuma divergência inesperada.

Comando oficial executado: python -m sheets_supabase_sync.batch_cli --config
runtime/forms_demo.config.json --dry-select, com READ ONLY e timeouts impostos
às conexões por PGOPTIONS/PGCONNECT_TIMEOUT. Resultado: sources_total=1,
sources_due=1, sources_failed=0, sources_executed=0, sources_skipped=0 e
sources_busy_deferred=0. O primeiro diagnóstico auxiliar falhou apenas ao
consultar o atributo de TLS do cliente; corrigido para conn.pgconn.ssl_in_use,
sem mudança no código do projeto e sem alteração de SSL/TLS.

Limites: presença de secrets não valida seus conteúdos; a configuração efetiva
do runner e a conectividade Google remota permanecem para a execução aprovada.
TLS ativo não comprova verificação da identidade do servidor; a pendência TLS
anterior permanece documentada, sem alterações neste gate.

Preflight GREEN, aguardando APROVAR 1 EXECUÇÃO MANUAL STAGING. Comando apenas
preparado, NÃO executado:
gh workflow run scheduled-sync.yml --repo DungeonCodes/sheets-supabase-sync --ref dev

Nenhum workflow_dispatch, sincronização real, escrita no banco, alteração de
secrets, migration, Cron, commit ou push. automation_remote_runner_validated
permanece pendente até execução única aprovada e reconciliação posterior.

## 2026-10-19 — preflight final do runner remoto (GREEN, aguardando aprovação)

Gate REMOTE_RUNNER_FINAL_PREFLIGHT. Segurança: o usuário confirmou a revogação
dos dois tokens Legacy; a triagem foi encerrada como MITIGATED com risco
residual documentado. Nenhum token novo, nenhum uso de PAT, nenhuma chamada à
Management API.

Preflight: `dev` em `1e0d218`, igual a `origin/dev` pela API do GitHub, sem
merge/rebase; única alteração local é este arquivo. O workflow `staging-dispatch`
(`scheduled-sync.yml`) está ativo, somente `workflow_dispatch`, sem execuções, e
o conteúdo remoto em `dev` é idêntico ao local. O Environment `staging` tem as sete
secrets, permite só a branch `dev`, sem revisores obrigatórios e com bypass de
administradores. O staging guard local passou com `APP_ENV=staging` e bloqueou
escrita sem confirmação. A configuração local tem uma fonte habilitada
(`forms_demo`); o conteúdo da secret `STAGING_SYNC_CONFIG_JSON` não é legível e
será conferido pelo resumo da primeira execução.

Baseline READ ONLY em `2026-10-19T11:14:45Z`: `SELECT 1` passou,
`transaction_read_only=on`, TLS no cliente ativo. O dry-select oficial retornou
`sources_total=1`, `sources_due=1`, `sources_failed=0`, `sources_executed=0`.
Contadores: `sync_runs=8` (todas `applied`), `raw_import_rows=11`,
`raw_current_rows=8`; iguais ao baseline de 18/10 e com deltas zero antes/depois
do dry-select (`n_tup_ins/upd/del` zero nas tabelas do escopo). Investigado:
`data_sources=2` porque `fixture_raw_staging` existe desde 13/08 (6 runs, última
em 17/08), fora da configuração e portanto fora do dispatcher; não é mudança.
O `ssl=false` de `pg_stat_ssl` mede o trecho pooler→Postgres, não o cliente.

Nenhum dispatch, sincronização, escrita, alteração de secrets, migration, Cron,
acesso a produção, commit ou push. Próxima aprovação: APROVAR 1 EXECUÇÃO MANUAL
STAGING. Este registro não autoriza execução.

## 2026-10-19 — preparação de rotação de tokens Supabase (YELLOW)

Gate SUPABASE_TOKEN_ROTATION_PREPARATION: inventário de PATs da conta não
acessível por canal autenticado seguro nesta sessão. A descoberta encontrou
plugin Supabase não conectado, sem capacidade de inventário de PATs confirmada.
Não foram utilizados tokens suspeitos nem reabertos históricos de credenciais.
Nenhum nome, data, tipo ou escopo de token da conta foi confirmado.

Os dois workflows versionados não referenciam SUPABASE_ACCESS_TOKEN nem
comandos da CLI Supabase; o dispatcher referencia sete secrets operacionais.
Não foi encontrada a variável de PAT nos ambientes de processo, usuário ou
máquina, nem o arquivo de fallback padrão da CLI. Isso não exclui credencial
no armazenamento nativo, perfis alternativos ou integrações externas.

Intervenção necessária: consultar manualmente Account > Access Tokens no
Dashboard e fornecer somente nomes, criação, expiração, Legacy/Scoped,
escopos e dependências conhecidas. Não copiar valores nem criar novos tokens.
Após o inventário, selecionar conservadoramente candidatos Legacy relacionados
à CLI de 18/10 e sem necessidade operacional confirmada, avaliar interrupções
e obter aprovação nominal antes de qualquer revogação. Tokens sem relação
demonstrada e as sete GitHub Secrets devem ser preservados.

Nenhum PAT novo é necessário para os workflows inspecionados. Se a CLI de
gerenciamento continuar necessária após a revogação, propor separadamente PAT
Scoped somente para staging, com permissões e validade mínimas. Evitar o fluxo
de login da CLI pelo navegador, que cria token clássico. Referência oficial:
https://supabase.com/docs/guides/platform/personal-access-tokens

Resultado YELLOW: candidatos e dependências externas ainda não identificados.
Nenhuma credencial criada, revogada, exibida ou testada; nenhum acesso a
produção, dispatch, alteração de secrets, migration, Cron, commit ou push.
Próxima aprovação: APROVAR REVOGAÇÃO CONTROLADA, condicionada à lista nominal
de candidatos e à avaliação das dependências. Este registro não autoriza execução.

## 2026-10-19 — resolução da sincronização Git

A branch dev foi atualizada por fast-forward para origin/dev (14b6672).
Os registros remotos de 18/10 e o registro local de 16/10 foram preservados
no mesmo arquivo, em ordem cronológica decrescente. Não houve commit, push,
pull, rebase ou alteração de código. Validação documental: diff sem erros
de whitespace, ausência de conflitos no índice e preservação das entradas.

## 2026-10-18 — retomada autorizada do staging e conectividade recuperada

Após aprovação explícita para reativar exclusivamente staging, a autenticação
existente da CLI foi utilizada com a Management API oficial. A identidade do
projeto foi reconfirmada contra o staging guard e a organização correspondente;
o estado era `INACTIVE` e o plano da organização foi confirmado como `free`.
Uma única chamada ao endpoint de retomada retornou HTTP 200. Consultas limitadas
acompanharam `COMING_UP`, `RESTORING` e finalmente `ACTIVE_HEALTHY`. Não houve
contratação, upgrade, criação de projeto ou alteração de credenciais.

O Session Pooler existente na porta 5432 voltou a aceitar a conexão PostgreSQL.
`SELECT 1` passou em transação `READ ONLY`, com `ssl_in_use=true`. O comando
oficial `python -m sheets_supabase_sync.batch_cli --config
runtime/forms_demo.config.json --dry-select` passou com uma fonte de demonstração
autorizada, identificada somente pelo alias sanitizado `demo-668bb049b1cf`:
`sources_total=1`, `sources_due=1`, `sources_skipped=0`, `sources_failed=0`,
`sources_executed=0` e `sources_busy_deferred=0`. Não houve chamada Google.

Baseline agregado em `2026-10-18T14:23:30.642291+00:00`: `sync_runs=8`,
`raw_import_rows=11` e `raw_current_rows=8`; zero runs planejadas ou em execução.
No escopo da demonstração: duas runs `applied`, três eventos `insert` e três
estados atuais. A última run da demonstração terminou em
`2026-09-24T10:43:23.402329+00:00`, com status `applied`. Os contadores globais
e da demonstração permaneceram iguais antes e depois do dry-select, deltas zero.

O diagnóstico TLS separado reproduziu falha de verificação da cadeia no cliente
Python, código 19 (`self-signed certificate in chain`). A configuração existente
usa `sslmode=prefer` implícito e a conexão PostgreSQL utilizou SSL; esse sucesso
não comprova verificação de identidade do servidor. Nenhuma política SSL,
connection string, secret, firewall ou código foi alterado.

Classificação: `staging_postgres_read_connectivity_recovered`. O próximo
checkpoint é aprovação de uma única execução manual do workflow na ref `dev`,
com baseline atualizado imediatamente antes do disparo e reconciliação posterior.
`automation_remote_runner_validated` permanece pendente. Não houve dispatch,
sincronização real, migration, Cron, acesso a produção, commit ou push.

## 2026-10-18 — preflight do runner remoto bloqueado por conectividade

Em `dev`, HEAD `edf47375218f978a67ae3d50dde6c32ce3732fc9`, o fetch confirmou
alinhamento 0/0 com `origin/dev`. O workflow `staging-dispatch` está ativo,
sem execuções registradas, e as sete secrets esperadas estão presentes no
Environment `staging`, restrito somente à branch `dev`, sem tags.

O staging guard local passou, assim como a validação estrutural da configuração
com uma única fonte de demonstração autorizada e do leitor Google read-only.
A tentativa de baseline usou conexão com `default_transaction_read_only=on`,
timeout limitado e queries agregadas; falhou na conexão antes de obter baseline.
O diagnóstico sanitizado confirmou DNS IPv4 e `ConnectionTimeout`, sem SQLSTATE.
Não foi possível determinar a causa de infraestrutura apenas por essa evidência.

O dry-select não foi executado. Não houve acesso Google, escrita no banco,
dispatch, migration, alteração de secrets ou ativação de recorrência.
Classificação: `automation_remote_runner_validation_blocked_connectivity`.
Próximo passo: recuperar conectividade PostgreSQL staging, repetir baseline e
dry-select read-only e somente então solicitar aprovação para uma execução remota.
O gate `automation_remote_runner_validated` permanece não atingido.

## 2026-10-16 — preflight do GitHub Actions remoto bloqueado

A raiz foi descoberta por `git rev-parse --show-toplevel`. O preflight confirmou
branch `dev`, worktree limpo e HEAD `edf4737`; após `git fetch origin`,
`origin/dev...dev` retornou `0/0`. Os documentos e entrypoints do gate foram
inspecionados, sem reabrir gates anteriores.

O workflow `scheduled-sync.yml` contém somente `workflow_dispatch`, runner
`ubuntu-latest`, environment `staging`, concorrência por ref com
`cancel-in-progress: false` e timeout de 20 minutos. Prepara Python 3.13,
instala o projeto e chama `python -m sheets_supabase_sync.batch_cli`; o YAML
limita-se à preparação operacional, sem lógica de seleção/sincronização.
Não foram identificados valores de secrets hardcoded. O workflow exige
`APP_ENV=staging` e executa o guard antes do dispatcher; o guard vincula
ambiente, project ref permitido e destinos Supabase/PostgreSQL. Os valores
remotos efetivos não puderam ser confirmados.

GitHub CLI 2.102.0 está disponível, mas `gh auth status` informou ausência de
autenticação. `gh workflow list` e `gh secret list` falharam por esse motivo;
a existência dos sete nomes esperados permanece não verificada, sem afirmar
que estejam ausentes.

Resultado: gate YELLOW, bloqueio de autenticação GitHub no preflight.
`automation_remote_runner_validated` não pode ser atribuída. Nenhum baseline,
disparo remoto, acesso Google/Supabase, migration, alteração de secrets,
recorrência, Cron, commit ou push foi executado. Nenhum segredo foi exibido.
Próximo passo: autenticação humana do GitHub CLI e retomada deste mesmo gate,
incluindo verificação das secrets, destino staging, baseline e uma única
execução manual, seguidos de reconciliação e revisão humana.

## 2026-10-02 — dispatcher central de staging v0.2

Foi implementado o entrypoint `python -m sheets_supabase_sync.batch_cli`. Ele
consulta `data_sources` em transação `READ ONLY`, deriva a última sync válida
de `sync_runs` aplicadas e finalizadas e executa somente fontes vencidas pelo
core staging existente. Fontes inativas, não vencidas, divergentes, busy e com
falha possuem resultado agregado sanitizado; uma falha não interrompe as
demais. `--dry-select` não acessa Google e não cria run ou linha raw.

Não foi criada nem alterada migration, DDL ou Cron. A migration 5 permaneceu
intocada. O workflow manual `scheduled-sync.yml` foi preparado para chamar o
dispatcher com concorrência serializada e timeout de 20 minutos, sem
`schedule`.

Os 47 testes direcionados passaram, assim como `compileall` e `git diff
--check`. O gate real executou apenas `--dry-select` contra staging usando a
fixture configurada: `sources_total=1`, `sources_due=1`, `sources_skipped=0`.
As contagens read-only antes/depois foram `sync_runs=8`, `raw_import_rows=11`
e `raw_current_rows=8`; todos os deltas foram zero. Não houve acesso a
production, Google, aplicação de batch, token GitHub ou segredo versionado.

Classificação: `automation_dispatcher_ready`. Próximo gate único: executar
uma vez manualmente o GitHub Actions no staging; não ativar Supabase Cron.

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

## Repetição do gate de conectividade PostgreSQL em 2026-08-13

Foi carregada a configuração privada local pelo mecanismo da aplicação, sem
exibir URL, host, Project Ref ou credencial. A variável PostgreSQL foi
identificada como endpoint Direct, na porta 5432, em vez de Session Pooler.
Como o gate exige interrupção nessa condição, nenhuma conexão foi aberta e
nenhum `SELECT`, `BEGIN`, advisory lock, rollback ou consulta de contagem foi
executado. Nenhuma escrita persistente, acesso Google, sincronização, migration
ou commit ocorreu. A versão local de `psycopg[binary]` confirmada foi 3.3.4.

Classificação: `blocked`. Próximo gate único: corrigir manualmente a
configuração privada para o Session Pooler na porta 5432 e repetir este mesmo
gate.

## Gate de conectividade PostgreSQL via Session Pooler em 2026-08-13

A configuração privada foi carregada exclusivamente pelo mecanismo da
aplicação. A presença de `SUPABASE_DB_URL` foi confirmada sem expor valor,
credencial, hostname ou Project Ref: o endpoint é Supavisor Session Pooler,
não é Direct e usa a porta 5432. O driver local confirmado foi
`psycopg[binary] 3.3.4`.

Em uma única tentativa com timeout curto, `psycopg` conectou e `SELECT 1`
retornou 1. Duas transações explícitas foram abertas; em cada uma,
`pg_try_advisory_xact_lock(hashtextextended(%s, 0))`, exatamente como no
adaptador, adquiriu uma chave fictícia sem bloqueio. Cada transação sofreu
`ROLLBACK`; a segunda aquisição da mesma chave retornou verdadeira, confirmando
a liberação do lock transacional.

Consultas somente de leitura confirmaram 0 linhas em `data_sources`,
`sync_runs`, `raw_import_rows`, `raw_current_rows`, `import_errors` e
`schema_change_requests`. As migrations locais/remotas estão em 3/3, sem
pendência ou divergência. Não houve escrita persistente, acesso Google,
sincronização, migration, `db push` ou commit.

Classificação: `postgres_connectivity_validated`. Próximo gate único:
autorização humana específica para a primeira sincronização integrada da
fixture exclusivamente fictícia.

## Idempotência integrada da fixture fictícia no staging em 2026-08-13

Após preflight verde, endpoint Session Pooler sanitizado, migrations 3/3 e
tabelas operacionais vazias, foram realizadas duas leituras read-only da
fixture previamente aprovada. Cada leitura retornou 5 linhas e 7 colunas, sem
retries e sem exibir conteúdo. O dry-run inicial previu 5 estados e 5 eventos
insert.

A primeira execução pelo fluxo transacional da aplicação criou exatamente uma
fonte, um `sync_run` aplicado, 5 estados `raw_current_rows` e 5 eventos insert
em `raw_import_rows`. A segunda leitura não reutilizou o snapshot anterior; a
segunda execução concluiu com 5 inalterados e não criou eventos adicionais.
As duas execuções usaram `psycopg`, transação PostgreSQL, advisory xact lock,
diff sob lock e commit. A inspeção somente por agregados confirmou 2 runs
aplicados, identidades únicas, versões 1, zero tombstones, zero updates/restores
e `import_errors=0`.

O schema permaneceu inalterado: migrations 3/3, RLS nas seis tabelas, zero
policies e lint verde. Não houve alteração da fixture, acesso a outra planilha,
migration, `db push`, SQL manual de escrita, nem commit Git. A suíte final
executou 150 testes, com 142 aprovados, 8 pulados e zero falhas.

Classificação: `integrated_idempotency_validated`. Próximo gate único:
autorização humana específica para testar mudança controlada da fixture
fictícia (update, tombstone, restore e reorder).

## Ciclo integrado de mudanças da fixture fictícia no staging em 2026-08-17

Quatro cenários foram executados um por vez, cada um após confirmação humana e
nova leitura Google somente de leitura. O update controlado gerou exatamente
um evento update e incrementou uma única versão de 1 para 2. A remoção de outra
identidade gerou um tombstone, preservando o estado e mantendo nulos os três
campos históricos exigidos. A restauração da mesma identidade foi reconhecida
como restore, não como inserção, e avançou sua versão de 2 para 3.

A reordenação física posterior gerou cinco registros inalterados, nenhum evento
adicional e nenhum incremento de versão. O estado final agregado é 5 estados,
8 eventos e 6 runs aplicados: 5 inserts, 1 update, 1 tombstone e 1 restore;
as versões são 3, 1 e 1 por distribuição, sem tombstone ativo e com
`import_errors=0`. Migrations permanecem 3/3, RLS continua nas seis tabelas,
policies permanecem em zero e lint está verde. Nenhum schema, grant, policy ou
configuração privada foi alterado.

Classificação: `integrated_change_cycle_validated`. Próximo gate único:
autorizar um teste controlado de schema drift da fixture fictícia.

## Checkpoint parcial de schema drift no staging em 2026-08-17

A baseline atual da fixture foi reconhecida por leitura read-only: 5 linhas, 7
colunas, fingerprint sanitizado equivalente e dry-run com 5 inalterados. A
política integrada compara schema sob advisory lock antes de `sync_run`, eventos
ou estado raw; adição, remoção e rename incerto são bloqueantes, não aprovam ou
sobrescrevem a baseline e deduplicam requests pendentes idênticas. Reorder de
headers é potencialmente compatível porque o parser mapeia valores por nome
normalizado; header duplicado é rejeitado pelo leitor antes da transação.

Coluna adicionada, removida e rename foram detectados e bloqueados sem alteração
de negócio. Eles produziram três `schema_change_requests` pendentes distintas.
Após cada restauração a fixture retornou a 7 colunas e 5 inalterados, sem sync
criada. O checkpoint final permanece com 5 estados, 8 eventos, 6 runs, zero
erros e eventos 5/1/1/1 por tipo.

Próximo gate único: cenário D, reorder controlado de headers.

## Gate completo de schema drift no staging em 2026-08-18

Após os cenários já bloqueados de coluna adicionada, removida e rename, o
reorder temporário de headers foi lido em modo read-only e tratado como
semanticamente compatível. O plano permaneceu com 5 inalterados e zero eventos;
identidades, hashes de conteúdo e versões de negócio foram preservados porque o
leitor associa valores por header normalizado, não por posição física. Nenhuma
`schema_change_request`, `sync_run`, linha raw ou baseline foi criada/alterada.

O cenário de header duplicado falhou no leitor com categoria sanitizada de
schema, antes de dry-run, transação ou acesso PostgreSQL. Após a restauração da
fixture, nova leitura e dry-run read-only retornaram 5 linhas, 7 colunas,
fingerprint equivalente e 5 inalterados. O estado final é 5 estados, 8 eventos,
6 runs, 3 requests pendentes e zero erros; eventos permanecem 5/1/1/1 por tipo
e não há tombstone ativo. Nenhuma escrita de negócio ocorreu neste gate.

Classificação: `schema_drift_validated`. Próximo gate único: falha/retry
operacional controlado, sob autorização humana específica.

## 2026-08-19 — resolução de conflitos de merge

Foram conciliadas as evoluções de schema/persistência PostgreSQL e de retry
operacional, preservando ambas as trilhas documentais. A validação local passou
com `compileall`, 165 testes (10 pulados) e `git diff --check`; nenhuma conexão
externa, migration, SQL ou commit foi executado.

## Gate local de retry operacional em 2026-08-24

Somente o PostgreSQL local do Supabase foi usado. As três migrations esperadas
estavam aplicadas. O adaptador passou a usar `connect_with_retry` para abrir a
conexão e converte falhas do driver no escopo transacional; falha de
reconhecimento depois do commit é classificada como `AMBIGUOUS_OUTCOME`.

O teste opt-in local comprovou advisory lock por fonte, busy sem criar fonte,
`sync_run` ou linhas raw, rollback nos quatro pontos controlados, nova
transação com lock/releitura/diff depois de falha transitória, e exatamente um
evento e um incremento de versão após retry. A perda controlada do
reconhecimento de commit não foi repetida automaticamente e preservou uma
execução aplicada para reconciliação pelo `sync_runs.id`. A evidência deste gate
foi produzida somente no PostgreSQL local. Uma chamada inicial a `supabase
migration list`, sem `--linked`, informou conexão remota inesperada e foi
interrompida; não houve escrita, push ou migration remota. Nenhum Google foi
usado.

## Compatibilidade remota read-only do retry operacional em 2026-08-24

O gate remoto autorizado usou somente leitura. `supabase migration list --local`
foi usado para a verificação local; em clones linked, essa flag é obrigatória
para gates estritamente locais. A comparação remota autorizada mostrou as três
migrations nos dois lados e `supabase db lint --linked` não encontrou erro.

O Session Pooler na porta 5432 aceitou `psycopg` pelo caminho normal de
configuração. Uma transação explicitamente `READ ONLY` executou `SELECT 1` e
agregados: 1 fonte, 5 estados, 8 eventos, 6 runs, 0 erros e 3 requests de
schema; as classificações de eventos são 5/1/1/1 e não há tombstone ativo. RLS
permanece ativo nas seis tabelas, sem policies, e `service_role` continua sem
DELETE nas tabelas raw. Não houve DML, lock, sincronização, fault injection ou
alteração de schema/grant/policy/RLS.

## Gate de observabilidade operacional e alertas em 2026-08-24

Eventos tipados e logs JSON sanitizados foram adicionados com severidades,
política explícita de alerta, deduplicação local e SMTP opcional mockado. Não
houve migration: `sync_runs` e `import_errors` mantêm seus contratos. Nenhum
e-mail, acesso Google ou staging foi usado; a suíte offline cobriu a fronteira
de alertas sem segredos.

## Gate de retenção, minimização e LGPD em 2026-08-24

Foi concluída auditoria offline de dados, classificação, minimização, retenção,
offboarding, ambientes e limites de backups. A política técnica recomenda
retenção limitada para histórico, erros, artefatos e observabilidade, sem alegar
prazo legal. O schema atual basta para auditoria/dry-run, mas automação segura
depende de proposta futura para hold e registro agregado de exclusão. Nenhuma
migration, purge, acesso Google, staging ou e-mail foi executado.

## Gate de desenho do schema de retenção em 2026-08-25

Preflight confirmou branch `dev` e worktree limpo. Baseline exclusivamente
offline passou com compileall, 183 testes (13 pulados), check-docs, pip check e
git diff check. As três migrations aplicadas foram lidas como texto; nenhum DDL
foi executado e nenhum serviço externo foi acessado.

O desenho mínimo ficou registrado na ADR
`20260825_retention_schema_design.md`: lifecycle em `data_sources`, holds
institucionais/por fonte, `purge_runs` separada de `sync_runs`, policy externa
versionada, dry-run sem DML, offboarding humano e evidência apenas agregada.
`raw_current_rows` permanece fora de purge histórico e sua FK
`last_sync_run_id` continua protegendo runs necessárias à reconciliação. A
proposta não cria migration, código, tabela, grant ou scheduler.

Classificação: `retention_schema_design_validated`. Próximo gate único: revisão
humana da ADR e autorização para criar somente localmente a migration 4 e seus
testes offline.

## Migration 4 de retenção validada localmente em 2026-08-25

Preflight confirmou branch `dev` e worktree limpo; a baseline executou 183
testes, com 13 pulados e zero falhas. A ADR e as três migrations existentes
foram relidas. Digests confirmaram que as migrations 1–3 permaneceram byte a
byte intactas.

Foi criada somente `20260825120000_add_retention_controls.sql`, com lifecycle em
`data_sources`, hold global/por fonte e `purge_runs`. A migration também reduziu
grants antigos ao contrato do sincronizador, sem conceder DELETE. Docker e
Supabase local foram iniciados; `supabase db reset --local` aplicou 4/4
migrations e `supabase db lint --local` passou. Nenhum comando linked ou push
foi usado.

Quatorze testes PostgreSQL locais passaram. Fixtures com lifecycle, holds,
evidência e tentativa de remoção de run referenciada foram revertidas. O
catálogo confirmou FKs, índices, RLS, zero policies, grants negativos e ausência
de trigger/procedure de retenção. Nenhum purge, Google, staging ou commit foi
executado.

Classificação: `retention_schema_local_validated`. Próximo gate único: revisão
humana do DDL, grants e evidência local antes de qualquer autorização separada
para staging.

## Revisão técnica read-only da Migration 4 em 2026-08-27

Preflight confirmou branch `dev`, worktree inicialmente limpo, compileall,
198 testes (19 pulados), documentação, dependências e diff sem falhas. As quatro
migrations e os documentos de retenção/segurança foram relidos. Git, blobs e
SHA-256 confirmaram as migrations 1–3 byte a byte intactas. No Supabase local,
`migration list` mostrou 4/4, lint passou e os seis casos PostgreSQL existentes
de retention controls passaram.

Provas adicionais, sempre em transações locais revertidas, mostraram que hold
institucional ativo permite excluir a fonte e iniciar `offboarding`. Hold de
fonte ativo bloqueia a exclusão da fonte com SQLSTATE `23514`, mas permite
`offboarding` e exclusão direta do histórico. Holds liberados, inclusive vários
históricos, permitem a retirada e preservam a evidência com FK nula. O banco
também não barra runs/raw para lifecycle não ativo. Em `purge_runs`, os CHECKs
básicos funcionam, mas executor/hold check, ordem aprovação-término, chaves e
valores dos JSONB e ausência semântica de PII não são garantidos pelo banco.

O staging foi inspecionado somente com `migration list --linked` e transações
PostgreSQL explicitamente read-only. Há 3 migrations remotas; a Migration 4 não
está aplicada. O schema das migrations 1–3, RLS, zero policies, grants e FKs
críticas foram confirmados. Existe uma fonte habilitada e nenhuma desabilitada,
compatível com o backfill. Não houve escrita remota, lock explícito, DDL, push,
purge, sync ou acesso Google.

Classificação: `requires_changes`. Próximo gate único: corrigir deliberadamente
o DDL/testes para tornar hold ativo e lifecycle não ativo barreiras efetivas;
depois repetir validação local e revisão read-only antes de nova decisão sobre
staging.

## Revalidação local corrigida da Migration 4 em 2026-08-27

Sem acesso remoto, Google, linked, push ou purge, as falhas anteriores foram
reproduzidas localmente: fonte offboarding aceitou sync/raw, holds não barraram
offboarding/delete e a evidence aceitou JSONB arbitrário, negativo e cronologia
inválida. A própria Migration 4 foi então corrigida; nenhuma Migration 5 foi
criada e os digests das migrations 1–3 permaneceram intactos.

O DDL agora usa guard de lifecycle em `sync_runs`, função central de hold e
triggers para lifecycle/delete/evidence. Cutoffs e contagens tornaram-se
colunas tipadas; evidence destrutiva exige aprovação anterior, executor e hold
check, e evidence terminal fica imutável no limite do owner/admin. O repositório
retorna `source_inactive` não repetível antes de criar run ou mutar raw.

Docker 29.7.2 e Supabase local estavam ativos. Dois resets locais aplicaram
4/4 migrations. Dez testes unitários da migration, oito de retention controls,
sete do repositório e dois operacionais PostgreSQL passaram; o script opt-in
totalizou 17 testes PostgreSQL aprovados. Nenhuma fixture de retenção foi
persistida fora dos testes locais. Classificação:
`retention_schema_local_revalidated`.

Próximo gate único: revisão humana da Migration 4 corrigida e da evidência
local antes de qualquer autorização separada para staging.

## Revisão técnica final da Migration 4 corrigida em 2026-08-27

Preflight confirmou branch `dev`; o worktree continha somente as correções e
evidências locais já esperadas da Migration 4. `compileall`, 203 testes offline
(22 pulados), documentação, dependências e diff passaram. Os SHA-256 das
migrations 1–3 permaneceram byte a byte intactos e o digest atual da Migration 4
é `02231058463cd2482b2406b7f23b7aaa56e862f3367bd3191c4b48621b0cee87`.

O catálogo local confirmou seis funções SECURITY INVOKER com `search_path`
restrito e EXECUTE direto revogado, dez triggers, RLS sem policies, grants
mínimos e FKs restritivas de current. Dez testes estruturais e 17 testes
PostgreSQL opt-in passaram; `migration list --local` mostrou 4/4 e o lint local
não encontrou erros.

Apesar da regressão verde, probes adicionais em transações revertidas
comprovaram quatro estados administrativos indevidos: `planned` destrutiva com
início/executor sem aprovação ou hold check; `failed` com contagem afetada
positiva sem início/executor/aprovação; aprovação posterior ao término; e
release de hold capaz de reescrever a evidência de ativação no mesmo statement.
O catálogo também confirmou ausência de triggers de `TRUNCATE`, e o SQL não
implementa a serialização institucional descrita para hold versus operação
destrutiva.

Classificação: `requires_changes`. Como o gate local não ficou integralmente
verde, staging não foi acessado. Não houve DDL/DML remoto, migration, push,
purge, sincronização ou acesso Google. Próximo gate único: corrigir a própria
Migration 4 e seus testes, reconstruir o PostgreSQL local e repetir esta revisão
antes de qualquer inspeção ou autorização de staging.

## Correção final local da Migration 4 em 2026-08-27

Sem acesso remoto, Google, linked, push ou purge real, foram primeiro
reproduzidas localmente as seis lacunas da revisão: estado destrutivo parcial,
terminal com efeito sem execução, aprovação posterior ao término, release que
reescrevia ativação, race de hold e bypass por TRUNCATE. A própria Migration 4
foi alterada, sem Migration 5; migrations 1–3 mantiveram seus digests.

O DDL final fecha a máquina de `purge_runs`, mantém `failed/cancelled` sem efeito
persistido, torna release append-only desde a transição inicial, introduz lock
advisory de retenção na ordem instituição/fonte e protege DELETE/TRUNCATE. A
evidência administrativa nunca pode sofrer TRUNCATE. Nove funções SECURITY
INVOKER têm search path restrito e EXECUTE direto revogado; nenhum grant foi
ampliado.

Três resets oficiais locais concluíram 4/4. O teste estrutural passou com 11
casos e o opt-in PostgreSQL passou com 24 casos, incluindo duas conexões reais
nas duas ordens de concorrência global e específica. `migration list --local` e
`db lint --local` passaram. Classificação:
`retention_schema_local_final_validated`.

Não houve staging, DDL/DML remoto, sincronização remota, Google, purge ou commit.
Próximo gate único: revisão humana read-only do DDL, grants e evidências locais
antes de qualquer autorização separada para staging.

## Aplicação controlada da Migration 4 no staging em 2026-08-31

Preflight em `dev` confirmou worktree limpo, quatro migrations, digests
imutáveis de 1--3 e SHA-256 autorizado da Migration 4. `compileall`, 211 testes
offline (29 pulados), `check-docs`, `pip check` e `git diff --check` passaram.
O baseline remoto READ ONLY confirmou migrations 3/3 e agregados operacionais
1 fonte, 6 runs, 8 eventos, 5 estados, 0 erros e 3 requests, sem run em curso.

Não havia tarefa agendada do projeto. O CLI não oferece `lock_timeout` para
`db push`; como não houve sessão de sync concorrente e o staging é pequeno, a
janela controlada foi considerada aceitável. O dry-run remoto listou somente
`20260825120000_add_retention_controls.sql`. O push oficial aplicou somente essa
migration e terminou sem erro.

`migration list --linked` confirmou 4/4 e `db lint --linked` não encontrou erro.
Uma transação posterior READ ONLY confirmou lifecycle `active:1`, metadados de
suspensão nulos, `retention_holds=0`, `purge_runs=0`, nove funções SECURITY
INVOKER, dezoito triggers, RLS sem policies, grants mínimos, cinco índices e FK
restritiva de current. Runs/history/current/errors/requests mantiveram os
agregados e distribuições técnicos do baseline. Não houve purge, hold,
offboarding, DELETE, TRUNCATE, sincronização, Google, seed, reset ou repair.

Classificação: `retention_schema_staging_applied_validated`. Próximo gate único:
autorização humana específica para rollout do código lifecycle, sem sincronização
neste gate.

## Fechamento do rollout lifecycle-aware em 2026-09-02

A aplicação validada da Migration 4 ocorreu no staging; ela não implica um
runtime de staging implantado. O código Python existente foi validado offline
para o rollout lifecycle-aware. `PostgresRawRepository` consulta `enabled` e
`lifecycle_status` sob `FOR SHARE` e retorna
`source_inactive`, não repetível, antes de criar uma run ou mutar raw quando a
fonte não está ativa. A migration mantém o guard equivalente no banco para novas
`sync_runs`.

Passaram 51 testes unitários de raw sync, falhas operacionais e controles de
retenção; `compileall`, `check-docs` e `git diff --check` também passaram. Não
houve conexão remota, SQL, sincronização, implantação de runtime, Google,
purge, hold, offboarding ou alteração de dados. Classificação:
`lifecycle_aware_code_rollout_closed`.

## Validacao multi-source local em 2026-09-02

O preflight em `dev` passou com 211 testes offline, 29 skips, `compileall`,
`check-docs`, `pip check` e `git diff --check`. A auditoria confirmou que
configuracao, estruturas operacionais, snapshots e advisory lock ja eram
orientados a fonte. A lacuna estava na prova integrada e na classificacao do
resultado do lote.

Foram adicionadas duas fixtures estritamente ficticias, `SOURCE_A` e
`SOURCE_B`, com schemas distintos e a mesma business key textual. A prova no
PostgreSQL local validou current/history/runs e versoes independentes,
idempotencia, updates isolados, tombstone/restore em A, drift apenas em A, lock
A/A busy com B livre, rollback e retry de A com B intacta, lifecycle apenas em
A e hold especifico sem alcance em B. A configuracao recusa pares
planilha/aba duplicados. O lote sequencial agora classifica sucesso, falha,
busy e inactive e gera resumo agregado sem payload ou identificadores externos.

`supabase migration list --local` confirmou 4/4 e os 25 testes PostgreSQL
passaram. A regressao final executou 218 testes: 214 aprovados, zero falhas e 4
pulados. As linhas de fixture foram removidas ao final do teste integrado. Nao
houve nova migration, acesso Google, staging, scheduler, purge, relacao entre
mirrors ou alteracao de `main`. Classificacao:
`multi_source_local_validated`. Proximo gate unico: definir o caso de negocio e
o contrato minimo da camada analitica.

## 2026-09-03 - Contrato analitico minimo

Preflight em `dev` confirmou worktree limpo. A orientacao oficial e os
documentos de requisitos, lacunas, plano, riscos, decisoes abertas, checkpoints,
arquitetura, roadmap, LGPD e multi-source foram revisados. Como nao existe
dominio real aprovado, o MVP foi limitado a fixture ficticia de
categoria/pontuacao.

Foi definido Star Schema corrente com `DIM_SOURCE`, `DIM_CATEGORY` e
`FACT_CATEGORY_SCORE`, identidade por fonte/business key, metricas count/avg/
min/max, consolidacao multi-source somente semantica, transformacao idempotente,
minimizacao LGPD, dois escopos futuros de leitura e quatro elementos de BI. A
fonte ficticia de curso/status nao alimenta essa fato; raw history e payload
nao sao promovidos. Nao houve teste, codigo, SQL, migration, acesso Google,
staging, Supabase, dashboard ou scheduler.

Classificacao: `analytical_contract_defined`. Proximo gate unico:
`analytical_schema`, somente local e sujeito a revisao humana do DDL.

## 2026-09-09 — Meeting MVP offline

Foi criado um dashboard HTML standalone e um conjunto executivo curto para a
apresentação da Atividade 3. O conteúdo separa explicitamente capacidades
validadas, implementadas sem validação completa, planejadas e demonstrativas.
O analytics usa somente dados sintéticos embutidos e não consulta Google,
Supabase, PostgreSQL ou qualquer serviço externo.

Os números apresentados foram limitados aos checkpoints existentes neste
clone: suíte de 150 testes (142 aprovados, 8 pulados, zero falhas), 3/3 testes
PostgreSQL locais, migrations 3/3 e ciclo fictício integrado com 6 runs, 8
eventos e 5 estados. Multi-source, retention/lifecycle, Star Schema físico,
RBAC, BI, scheduler e E2E permanecem pendentes. O dashboard foi aberto em
navegador local e o filtro de fonte recalculou KPIs, gráficos e tabela.

## 2026-09-09 — revisão de acurácia do Meeting MVP

Os artefatos da reunião foram reconciliados com os gates posteriores autorizados,
pois a documentação presente neste clone conserva números e classificações mais
antigos. A apresentação agora registra o pipeline operacional, retry/rollback,
commit ambíguo, observabilidade e alert policy como validados; multi-source como
validado localmente; e retention/lifecycle como aplicado e validado em staging
pela Migration 4.

Os indicadores foram atualizados para 218 testes totais, 214 aprovados, 4
pulados, zero falhas, 25 testes PostgreSQL multi-source, 4/4 migrations e duas
fontes fictícias isoladas. O analytics permaneceu como demonstração offline com
dados fictícios. Foi criado `docs/meeting/evidence-register.md` para preservar a
referência dos gates e impedir nova regressão documental.

## 2026-09-09 — composicao staging implementada e validada offline

Foi implementada a composicao segura entre o Google reader, snapshot/diff e o
repositorio raw PostgreSQL. O novo entrypoint remoto e separado de `apply-local`,
oferece dry-run e exige confirmacao explicita para escrita em staging. O guard
rejeita production, ambiente desconhecido e destino PostgreSQL que nao possa ser
vinculado ao project ref permitido.

O repositorio agora valida integralmente os atributos persistidos de uma source
existente e aplica o lifecycle disponivel no schema (`enabled`) antes de qualquer
run ou linha raw. Retry transacional recarrega estado e recalcula o diff; commit
ambiguo reconcilia run, eventos e current state antes de concluir ou repetir.

A suite offline executou 193 testes: 183 aprovados, 10 pulados e zero falhas. Os
pulados exigem Google real, PostgreSQL/Supabase local ou teste de performance
opt-in. `git diff --check` e o check documental passaram. Nenhuma rede, Google,
Supabase, Docker, migration ou sync real foi usada. Classificacao:
`staging_sync_core_offline_validated`.

## 2026-09-19 — integração de mudanças locais e remotas

Foi integrado o branch remoto `origin/dev` aos controles de sincronização de
staging locais. A resolução preserva a reconciliação de commit ambíguo, a
validação fechada de source e o guard de staging, além de lifecycle,
observabilidade, multi-source, retenção e o schema analítico do remoto.

Os testes de integridade das migrations foram ajustados para calcular SHA-256
sobre conteúdo canônico com LF; isso preserva a comparação entre migrations e
elimina a divergência de CRLF nos checkouts Windows. A validação final executou
224 testes, com 30 pulados por dependerem de infraestrutura local. Nenhuma
migration, SQL, conexão Google ou sincronização remota foi executada.
## 2026-09-11 — fluxograma executivo do sheets-supabase-sync

Foi criado `docs/diagrams/sheets_supabase_sync_flow.drawio`, em uma página,
com o fluxo validado de Google Sheets até o estado raw e a evolução analítica
claramente marcada como planejada. O diagrama inclui a faixa transversal de
segurança e resiliência e não afirma operação produtiva. Como não havia CLI
Draw.io disponível no ambiente, também foi criado o fallback Mermaid
`docs/diagrams/sheets_supabase_sync_flow.md`; SVG e PNG não foram gerados.
Nenhum código, migration, serviço externo, banco ou dado foi acessado.

## 2026-09-11 — fluxograma operacional proposto

Foi criado `docs/diagrams/sheets_supabase_sync_operational_flow.drawio` como
artefato separado do fluxograma técnico. O desenho organiza Cliente, Inicie,
Aplicação/Pipeline, Google/Supabase e BI/Consumo em swimlanes; distingue o MVP
assistido da evolução self-service e mantém analytics/BI como futuro. As
responsabilidades de produto ainda abertas aparecem como decisões para validar
com a Inicie. Também foi criado o fallback Mermaid correspondente. Nenhum
código, migration, serviço externo, teste ou dado foi acessado.

## 2026-09-11 — ADR de execução agendada do MVP

Foi criada a ADR proposta
`docs/decisions/20260911_scheduled_sync_mvp_architecture.md`. Ela documenta
GitHub + Vercel + Supabase, Supabase Cron como despertador global, Vercel
Function Python como worker condicionado a validação, periodicidade diária
inicial, segurança server-side, alternativas, riscos e critérios objetivos de
aceitação e revisão. Também foi atualizado o resumo `docs/decisions.md`.
Nenhuma implementação, migration, integração externa, secret ou deploy foi
executado.

## 2026-09-30 — reconciliação da idempotência forms_demo e audit v0.1

Precheck: branch `dev`, HEAD `663ccee2b06c4882e18ff783cebe8492acdd305f`,
worktree limpo antes deste registro; projeto linked igual ao permitido,
`APP_ENV=staging`, production=false e staging guard aprovado. A nova leitura
Google read-only retornou 3 linhas, 4 colunas, zero retries e passou pelo
validador da fixture fictícia. Uma segunda leitura confirmou que o snapshot
corresponde semanticamente ao estado raw e ao hash da última run.

O baseline remoto revelou que a segunda sync já havia sido executada em
2026-09-24, antes deste gate. As duas runs de `forms_demo` estão `applied` e têm
o mesmo hash de snapshot. A primeira registrou 3 inserts/3 eventos; a segunda
registrou 3 unchanged, zero inserts/updates/tombstones/restores e zero eventos.
O current tem 3 linhas ativas, todas na versão 1. Assim, a segunda sync existente
comprova deltas zero em current e nos quatro tipos de evento, com `sync_runs` +1.
Nenhuma terceira sync foi executada. Classificação do E2E operacional:
`forms_demo_e2e_idempotency_validated`.

No audit mínimo da v0.1, o entrypoint `staging_cli --mode dry-run` falhou com
categoria `database`. A causa foi reproduzida sem escrita: `SELECT ... FOR SHARE`
na transação `READ ONLY` retorna SQLSTATE 25006. O README ainda não fornece o
comando de staging, e apresenta estado/testes/limitações anteriores aos gates
atuais. Esses são bloqueadores da entrega operacional até correção e validação
direcionada. `pip check`, imports do entrypoint e `--help` passaram. Configuração
local e credenciais não estão versionadas. Não houve migration, SQL de escrita,
mudança Google, alteração de source, sync adicional, release ou push.
Classificação da entrega: `v0_1_blocked`.

## 2026-09-30 — desbloqueio do dry-run e documentação operacional v0.1

O precheck permaneceu em `dev`, HEAD `663ccee2b06c4882e18ff783cebe8492acdd305f`.
O histórico local, reflog e objetos Git não continham a correção específica do
lookup sem lock. Foi reaplicada uma alteração mínima: preview e reconciliação
mantêm `READ ONLY` e consultam a source sem `FOR SHARE`; escrita conserva o
`FOR SHARE` padrão. Testes direcionados de raw sync, falhas operacionais,
staging e repositório PostgreSQL: 68 executados, 61 aprovados, 7 pulados por
dependerem de PostgreSQL local, zero falhas.

O primeiro dry-run após o ajuste de código retornou `source_mismatch`: somente
`target_table` no arquivo local ignorado diferia da source existente. A
configuração local foi alinhada ao identificador já registrado, sem alterar a
source remota. O dry-run real seguinte retornou `snapshot_rows=3`, 3 unchanged,
zero inserts/updates/tombstones/restores e `persisted_rows=0`.

Antes e depois, `raw_current_rows=3`, `sync_runs=2` e `raw_import_rows=3`.
O fingerprint técnico de current permaneceu igual; o catálogo manteve 34
relações públicas e o histórico remoto manteve 4 migrations aplicadas. Não
houve DDL, DML, terceira sync, acesso a production, push ou release. O README
recebeu somente o fluxo operacional assistido de staging e o estado atual da
v0.1. Classificação: `v0_1_ready_for_delivery`.

## 2026-09-24 — correção do preview PostgreSQL read-only

O lookup de `data_sources` passou a aceitar explicitamente consulta sem lock nos
fluxos PostgreSQL `READ ONLY` de preview e reconciliação. O caminho de escrita
continua usando `FOR SHARE`. Os testes direcionados executaram 93 casos: 86
aprovados, 7 integrações locais puladas por ausência de `LOCAL_DATABASE_URL` e
zero falhas.

O preview real de `forms_demo` leu 3 linhas e calculou 3 inserts, zero updates,
zero tombstones e zero restores contra zero linhas atuais. Leituras remotas
agregadas, ambas em transações `READ ONLY`, confirmaram antes e depois zero
`sync_runs`, zero `raw_import_rows` e zero `raw_current_rows` para a fonte. Não
houve migration, DDL, acesso a production nem sync real. Classificação:
`forms_demo_preview_validated`. O próximo gate é a primeira sync real de
`forms_demo`, sujeita a autorização separada.

## 2026-09-30 — preparação do disparador manual GitHub Actions

O precheck da v0.2 iniciou em `dev`, com worktree limpo e HEAD
`ff044df5cdbf46366f14b84246577c0392737872`. O entrypoint oficial de staging
foi auditado: ele exige config multi-source, nome de source, modo
`apply-staging` e confirmação explícita; o staging guard valida ambiente,
project ref, URL Supabase e destino PostgreSQL antes de escrever.

Foi preparado o workflow manual `staging-sync-dispatch`, sem `schedule:`. Ele
instala o projeto, cria configuração efêmera a partir de GitHub Environment
secrets, valida o guard e chama exclusivamente o entrypoint existente. A
concorrência não cancela execução em andamento. Não houve workflow remoto,
sync, dry-run, chamada Google/Supabase, Cron, token, migration, DDL ou acesso a
production.

O domínio já possui `due_sources`, mas a seleção é parcial: o staging CLI não
carrega estado operacional atualizado de `last_sync_at` nem consulta agenda no
banco. O futuro Cron global depende de dispatcher Python central; quantidade de
fontes e capacidade permanecem decisão pendente do Eric.
