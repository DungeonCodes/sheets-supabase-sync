# SUPABASE_CRON_VS_GITHUB_ACTIONS_SCHEDULE

## Atualização humana — GITHUB_CLOCK_MANUAL_VALIDATION_PREPARATION, 20/10/2026

**Alternativa B APROVADA como arquitetura candidata principal**, exclusivamente
no plano arquitetural. Não autoriza publicação, dispatch ou schedule. O texto
comparativo original abaixo é preservado como histórico da proposta.

Preparação offline GREEN: [revisão e plano manual](../../drafts/github_scheduler/MANUAL_VALIDATION.md).
V1/v2 e testes históricos preservados; candidato manual separado, sem schedule,
com autorização pelo número exato da run, registro anterior ao POST e helper
offline para detectar falhas por fonte apesar de exit code zero. Executor
validado permanece intacto. Supabase Cron/Edge continua alternativa estudada,
não implantada, com evidências/probe preservados e autenticação ainda pendente.

Próximo gate: **GITHUB_CLOCK_MANUAL_PUBLICATION**. Aprovação requerida:
**APROVAR PUBLICAÇÃO MANUAL DO RELÓGIO NA MAIN**, sem autorização implícita de
executar teste, configurar enable ou recorrência.

Gate: SCHEDULER_ARCHITECTURE_DECISION. Data: 20/10/2026.
Status: **PROPOSTA — YELLOW para ativação; alternativa B tecnicamente viável**.

Recomendar relógio GitHub Actions separado na main, token temporário do job e dispatch fixo para o executor existente na dev/environment staging. Não implementar recorrência, definir frequência, publicar workflow ou executar teste remoto neste gate. Aprovação arquitetural não autoriza essas ações.

Esta revisão complementa, sem apagar ou editar, a [proposta de 19/10](20261019_scheduler_architecture_decision.md), o [pacote anterior](../../drafts/github_scheduler/README.md) e todos os rascunhos Cron/Edge/probe. Para revisão futura usar apenas o novo draft v2; o original permanece histórico, não deve ser publicado junto.

## Preflight e evidências atuais

- Host DESKTOP-VU6VMS6; raiz `C:/Users/tisap/Documents/GitHub/sheets-supabase-sync`; branch dev; HEAD `b84f1b2eeca0f9ffe3fa135ba03f2468eb3928e9`; worktree inicialmente limpa.
- Origin: repositório GitHub `DungeonCodes/sheets-supabase-sync`. Consulta read-only ls-remote: dev no mesmo HEAD; main `88ae3008140905ce05a4fcf7c01bc6db72db6c78`. Sem fetch/pull ou operação de escrita Git.
- Lidos AGENTS.md, docs/master_context.md e docs/agent_rules.md. Contexto mestre ainda é esqueleto; objetivo/entradas/saídas/aceitação desta decisão provêm da instrução humana explícita deste gate.
- GitHub GET: público, default_branch main, não arquivado/desabilitado, Actions enabled, allowed_actions all, pinning obrigatório false. Default_workflow_permissions **read**, aprovação de PR pelo token false. Não presumir actions:write por padrão.
- Executor scheduled-sync.yml ativo, workflow ID 388468858. Blob local, main e dev idêntico: `65d16e28a9e00918a0eac2213ab57b0e73fc6ea0`.
- Run 39247320871 consultada só por metadados: completed/success, workflow_dispatch, dev, attempt 1. Não repetida. Gate remoto GREEN e probe transacional GREEN preservados; 9/11/8 e fontes 1 executada/1 no_changes/0 failed são evidência anterior, não nova leitura PostgreSQL.
- Environment staging: custom_branch_policies=true, protected_branches=false, única política branch **dev**, nenhuma tag. Sem required reviewers retornados; can_admins_bypass=true. Nenhuma configuração alterada.
- Sete environment secrets conferidas somente por nomes: APP_ENV, SUPABASE_PROJECT_REF, SUPABASE_ALLOWED_PROJECT_REF, SUPABASE_URL, SUPABASE_DB_URL, GOOGLE_SERVICE_ACCOUNT_JSON, STAGING_SYNC_CONFIG_JSON. Valores inacessíveis por esta consulta. Repository secrets=0 e repository variables=0. Não é possível reconfirmar valores de APP_ENV/refs por metadata; a validação runtime existente e o gate GREEN são a evidência disponível.
- Nenhuma chamada Google, Supabase, SQL, dispatch, instalação, benchmark ou produção. Credencial da CLI local usada apenas para GETs de governança não prova permissões de um futuro GITHUB_TOKEN.

## Comparação

| Critério | A: Cron → pg_net → Edge autenticada → GitHub → Python | B: clock main → GITHUB_TOKEN → dispatch dev → Python |
|---|---|---|
| Segurança | Origem Cron continua não comprovada sem expor credenciais na fila; probe GREEN não resolve autenticação HTTP | Identidade nativa temporária do job, sem segredo Google/DB no relógio; actions:write ainda tem alcance amplo no repo |
| Simplicidade | Job DB, extensão/fila, autorização SQL, Edge, credencial GitHub, runner e conciliação | Um workflow adicional e o executor já validado; sem endpoint novo |
| Tokens | Integração desenhada requer credencial GitHub externa e identidade/segredo de ingresso confiável | GITHUB_TOKEN emitido automaticamente, job-scoped; nenhum PAT adicional |
| Custos | DB, fila, Edge/egress e gestão de credenciais; marginal não medido | Runner padrão público gratuito na regra atual; armazenamento, limites e trabalho operacional permanecem |
| Confiabilidade | Mais fronteiras e serviços; não demonstrada ponta a ponta com origem segura | Schedule pode atrasar/ser descartado; não oferece pontualidade garantida |
| Observabilidade | Correlacionar Cron/fila/autorização/Edge/GitHub/dispatcher | Parent run_id → child run_id retornado pela API → deployment/job → contadores do dispatcher |
| Duplicidade | Claim/expiração ajudam no controle; ingresso seguro ainda pendente | Concurrency + busy skip + locks do domínio; não há deduplicação durável/exactly-once |
| Falhas | Mais cenários de transporte, autenticação e resposta ambígua | Uma tentativa POST; ambiguidade bloqueia replay, inspeção humana primeiro |
| Staging | Exige implantar componentes ainda não aprovados | Reutiliza dev/staging e staging guard sem alteração |
| Manutenção | Roles/grants, token/rotação, funções DB/Edge, fila e deploy | Políticas GitHub, revisão de código, logs/retention, inatividade e monitoramento |
| Múltiplos clientes | Não elimina elegibilidade por fonte nem gestão de identidade por cliente | Relógio central continua simples; dispatcher decide intervalo por fonte; escalar isolamento por cliente conforme requisitos |

A fica **YELLOW, preservada como histórico/opção futura**, sem reabrir o probe ou implantar o redesign. B é recomendada por remover fronteiras de autorização e credenciais adicionais desnecessárias para esta necessidade. Se houver SLA estrito, necessidade de fila garantida, volume acima do timeout ou isolamento forte entre clientes, reavaliar scheduler/worker; não prometer que B atende esses requisitos ainda desconhecidos.

## Viabilidade GitHub — treze pontos

1. **Schedule usa a branch padrão**, atualmente main, e requer workflow presente nela. Não basta arquivo na dev. A regra é default branch, não um nome main imutável.
2. **Dispatch do mesmo repositório com GITHUB_TOKEN é suportado**; workflow_dispatch é exceção à supressão usual de eventos disparados pelo token. Endpoint exige Actions:write e aceita ref dev. Declarar permissões no job; read atual é insuficiente para POST.
3. **Staging permanece dev-only**, conforme política real acima. A presença de scheduled-sync.yml em main não libera environment secrets para main.
4. **As sete secrets permanecem no environment**. O relógio não declara environment nem referencia secrets de dados. Limite importante: política de branch não é allowlist de arquivo de workflow. Qualquer job autorizado na dev que referencie staging pode potencialmente acessá-las. Não afirmar exclusividade criptográfica de scheduled-sync.yml. Revisão de alterações de workflows e acesso de escrita dev/main é requisito de governança; alteração maliciosa da dev ainda é risco. Nenhuma proteção de branch adicional foi presumida ou configurada.
5. **Relógio sem credenciais Google/Supabase**. Sem checkout, pip/Python, dependências ou actions terceiras; somente token automático. Segredos não são transferidos do pai ao filho.
6. **Executor Python reutilizado sem mudança**: manual workflow_dispatch, checkout da revisão dev selecionada, Python 3.13, instalação do projeto, configuração efêmera, guard e batch_cli --confirm-staging; cleanup always. Não é necessário transformar em reusable workflow/workflow_call.
7. **PAT adicional não é necessário**. Se política impedir token write ou POST for recusado, bloquear; não aumentar permissões globais nem criar fallback de token.
8. **Correlação**: contrato atual da API 2026-03-10 documenta HTTP 200 com workflow_run_id/run_url/html_url. V2 envia só `{ref:'dev'}`; remove o parâmetro return_run_details usado no draft histórico e não listado na referência atual consultada. Validar URLs/ID e GET do filho por workflow_id/event/ref/SHA/attempt. Registrar parent e child IDs. Se resposta se perder após POST, pesquisar por janela/ref/SHA/ator apenas como candidatos; sem input de correlação no executor, não garantir identificação inequívoca. Não reenviar automaticamente.
9. **Concorrência e retries**: grupos distintos para pai/filho; cancel-in-progress=false. Consultar runs ativos do destino, skip se ocupado; preflight não é lock e está sujeito a corrida manual. Concurrency padrão do executor mantém um ativo e um pendente; uma chegada pode substituir pendente. Rerun do relógio recusado (attempt !=1), um POST por execução, zero retry automático no relógio. Isso não impede novo run manual distinto nem deduplica autorização. Locks por fonte/idempotência continuam a defesa transacional existente.
10. **Execução perdida**: antes de recorrência, definir tolerância L, calendário, responsável e observador fora da cadeia deste relógio. Comparar expected_tick_at + L com runs schedule da main por created/event/ref; depois comparar último tick aceito com child concluído e contadores. Ausência de run não produz log/notification de falha: requer leitura independente ou checklist humano no SLA acordado. Monitor externo de leitura é proposta, não foi criado nem recebeu token. Sem observador/responsável definido, recorrência permanece bloqueada.
11. **Atraso/descarte**: GitHub documenta ambos sob carga. Evitar começo da hora ao escolher horário; frequência não definida. Tick seguinte pode encontrar fontes ainda due conforme aplicação, sem reconstituir artificialmente cada tick perdido. Falha ambígua anterior exige inspeção antes de nova tentativa manual. Não há replay automático de dispatch no relógio.
12. **Inatividade**: repositório público pode ter schedule desabilitado após 60 dias sem atividade. Verificar workflow state, idade do último tick real e ator ativo; alertar responsável e reativar somente após revisão humana conforme documentação. Não criar commits artificiais nem PAT para contornar. Schedule pode parar por situação do ator; avaliar também esse caso.
13. **Main não sincroniza diretamente**: job clock não tem environment nem secrets de dados; se executor main tentar staging, a política dev bloqueia antes de disponibilizar secrets. Payload fixa dev. Token actions:write não pode ler environment secret values nem editar conteúdo do repo com contents:read, mas pode disparar outros workflows: confiança no código do clock/main continua necessária. Não há defesa contra administrador alterando políticas ou escritor autorizado alterando código dev; não confundir proteção atual com isolamento absoluto.

## Falha fechada e staging guard

Permissões v2: topo `permissions: {}`, job clock com apenas `actions: write` e `contents: read` (esta última para ler revisão dev). Sem environment. Nenhuma secret de dados é injetada no job. APP_ENV=staging e correspondência SUPABASE_PROJECT_REF/SUPABASE_ALLOWED_PROJECT_REF continuam exigidas pelo executor/validate_staging_access; produção é recusada. Não verificar valores secretos por impressão/log/artifact.

| Condição | Comportamento previsto |
|---|---|
| Contexto/ref/ator do evento impróprio, rerun, opt-in ausente, SHA/expiração inválida | Bloquear antes de POST; não acessar staging |
| Token ausente, 401/403 ou erro de preflight | Falhar sem dispatch nem retry; sem fallback PAT |
| Executor ocupado ou observação de concorrência inconclusiva | busy_skip explícito ou bloqueio; nenhum novo POST |
| POST rejeitado | Terminar sem retry; resposta não 200 fica categoria conservadora bloqueada/ambígua; inspeção identifica rejeição, sem expor corpo |
| Timeout/204/200 inválido/GET de observação perdido após POST | Marcar ambiguidade, preservar ID se conhecido; pode haver filho em execução, não afirmar zero sincronizações |
| Branch/environment bloqueado no filho | GitHub impede job/secrets; pai aceito não significa sync bem-sucedida; observar filho |
| Secret ausente ou APP_ENV/refs inválidos | Shell/guard recusa antes de batch_cli; cleanup always |
| dev muda entre preflight e dispatch | Comparação posterior detecta, mas não impede início com outro SHA; congelar dev na validação manual; guard estrito no destino seria trabalho futuro separado |

Gate de origem do relógio não altera os retries transacionais seguros já implementados no domínio Python. Não criar retries de workflow, dispatch ou de commit ambíguo. Não usar cancelamento durante commit como rollback.

## Frequência, contadores e custos

O relógio não seleciona fontes. `select_sources_due` usa configuração por fonte, enabled, lifecycle, identidade e último sucesso + sync_interval_minutes. `dispatch_sources` executa apenas DUE. Fontes incompatíveis são INVALID e contam como falha, não skipped silencioso. Contadores preservados: sources_total, sources_due, sources_executed, sources_no_changes, sources_skipped, sources_failed, sources_busy_deferred. Busy é adiado; um tick posterior pode reavaliar elegibilidade.

Constatação relevante: `batch_cli.run_cli` retorna 0 após resumo mesmo quando sources_failed>0 ou busy_deferred>0; status completed e GitHub verde não comprovam sucesso de todas as fontes. Monitoramento precisa verificar resumo sanitizado e reconciliar falhas/último sucesso por fonte. Não modificar CLI nem gate GREEN aqui. A integração desse sinal ao observador é critério antes da recorrência, ou propor ajuste explícito em outro gate.

Mesmo com zero due, runner faz startup, checkout, setup Python, pip install e consulta do estado operacional no PostgreSQL; não consulta Sheets por fonte inelegível. Há custo de latência, conexão DB, logs e concorrência, além do custo financeiro conforme plano. Não fazer benchmark. Estimativa paramétrica: ticks/mês = duração_mês/intervalo_tick; minutos runner = ticks × (tempo_clock + tempo_executor), inclusive ticks sem due. Frequência, volume e durações permanecem não definidos; não inventar mensalidade.

Repo público + ubuntu-latest padrão: execução de runner gratuita na regra oficial atual. Estimativa marginal de compute Actions **US$ 0 sob essas condições**, não custo total zero; retenção/storage/egress/Supabase continuam sujeitos a plano/uso. Migrar para privado ou usar larger runners requer recalcular. A adiciona consumo DB/Edge/fila/egress e gestão de secrets, sem medição neste gate.

Para múltiplos clientes, manter intervalos e seleção na aplicação; não um Cron por planilha. Config atual é institucional; eventual fan-out multi-instituição/isolamento de credenciais exige desenho próprio, limites de tempo/volume e autorização por cliente. Não alegar suporte multi-tenant isolado já implementado.

## Preparação offline, aceitação e implantação em duas etapas

V2: [staging-clock-v2.draft.yml](../../drafts/github_scheduler/staging-clock-v2.draft.yml), apenas drafts/. Apenas gatilho manual, sem schedule/cron. Código prevê evento schedule para revisão futura, mas nenhum evento recorrente foi publicado. Mantidas confirmação, opt-in, SHA e janela curta de aprovação para o teste manual; **janela de 15 min não é frequência nem política permanente**. Para etapa B revisar política de revisão/SHA/expiração recorrente; não depender de renovar approval a cada tick indefinidamente.

Testes: `node --test tests/cron_dispatch/github-clock-v2.test.mjs` **34/34 PASS**, programa exato extraído do YAML com fetch/process/tempo/logs simulados; cobre payload, identidade, permissões/ausência de secrets, erros/rede/timeout, concorrência/paginação, resposta ambígua, correlação e guard do executor. Testes históricos **32/32 PASS**. Dispatcher: `.venv/Scripts/python.exe -m unittest tests.unit.test_dispatcher -v` **7/7 PASS**, offline com dependências simuladas; elegibilidade e contadores, sem banco/Sheets. Não instalado parser YAML; validação hospedada e permissões do token emitido só podem ser provadas no gate manual futuro. Sem novas dependências, produção ou alteração Python.

Etapa A, somente após aprovação humana específica:

1. Revisar ADR, único draft v2, acesso de escrita/main/dev e branch policy staging; preservar segredos exclusivamente no environment. Aprovar separadamente publicação **manual-only**, opt-in inicialmente ausente/desabilitado. Nenhum desses passos executado agora.
2. Publicação humana apenas do relógio na main; não alterar executor validado. Conferir diff, ausência de schedule e ausência de environment/credenciais no clock. Congelar revisão dev durante janela controlada.
3. Autorizar uma tentativa do novo relógio, com opt-in/SHA/janela revisados. Isso pode iniciar nova sync staging e precisa de autorização própria; não é repetição automática do gate remoto GREEN. Conferir permissões emitidas, parent/child IDs e branch/environment antes de concluir validação.
4. Observar conclusão do filho, guard, contadores e reconciliação apropriada de staging; retirar opt-in após teste. 403/ambiguidade bloqueiam sem replay. Critério: uma tentativa, filho correlacionado na dev, ambiente correto, zero acesso direto do relógio aos segredos de dados.

Etapa B, outra autorização humana posterior: definir frequência por fonte e tick, tolerância/observador independente, resposta a falhas e inatividade, retenção e política de autorização duradoura. Só então revisar/adicionar schedule na main e observar primeiro evento schedule real. Manual não prova entrega schedule. Sem responsável/observador e tratamento de resumo sources_failed, não ativar.

Rollback futuro: desabilitar somente clock/opt-in; remover schedule por mudança humana revisada se já existir. Preservar scheduled-sync.yml manual e environment/secrets. Verificar runs pai/filho já aceitos; disabling não desfaz dispatch ou commit. Acompanhar e reconciliar execução em curso; não aplicar SQL reverso, migration, novo disparo compensatório ou cancelamento automático. Nada ativo agora exige rollback.

## Fontes oficiais consultadas em 20/10/2026

- [Eventos e schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule): default branch, atraso/descarte, inatividade pública e ator.
- [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token): emissão por job, escopo do repo e exceção workflow_dispatch.
- [Permissões](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions): declaração por job e cálculo das permissões.
- [REST dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event): ref, Actions:write, HTTP 200 e IDs/URLs; v2 usa body somente ref.
- [Environment e secrets](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments): elegibilidade por branch e disponibilidade de segredos no job.
- [Concorrência](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency): execução ativa/pendente e limites de serialização; não é exactly-once.
- [Custos Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions): runner padrão público gratuito, demais recursos/planos sujeitos a limites.

## Resultado obrigatório

```text
STATUS: YELLOW
CURRENT_REMOTE_RUNNER: GREEN
TRANSACTIONAL_PROBE: GREEN
SUPABASE_CRON_OPTION: YELLOW; origem autenticada pendente; preservar histórico
GITHUB_SCHEDULE_OPTION: VIABLE; draft manual-only revisado/testado, recorrência não autorizada
GITHUB_TOKEN_DISPATCH_SUPPORTED: YES (documentado; token emitido/handoff ainda não testados)
STAGING_ENVIRONMENT_PRESERVED: YES
ADDITIONAL_PAT_REQUIRED: NO
SCHEDULER_RECOMMENDATION: B — relógio main, dispatch dev, executor staging existente
JUSTIFICATION: menos componentes/credenciais, reaproveita runner e elegibilidade Python
SECURITY_RISKS: Actions:write amplo; confiança em main/dev; secrets não vinculadas exclusivamente a um workflow; ref dev móvel
OPERATIONAL_RISKS: atraso/perda/inatividade; corrida e substituição de pending; ambiguidade; falhas por fonte com exit code 0
ESTIMATED_COST: compute Actions US$ 0 para runner padrão público; demais custos variáveis, mensalidade sem frequência não estimável
FILES_PREPARED: draft v2, testes v2 e esta ADR; histórico preservado, run_log/índice atualizados
TEST_RESULTS: 34 v2 + 32 históricos + 7 dispatcher PASS; zero chamadas operacionais nos testes
ROLLBACK_PLAN: desabilitar somente clock/opt-in, observar filhos aceitos, preservar executor e secrets
NEXT_GATE: GITHUB_CLOCK_MANUAL_VALIDATION_PREPARATION
HUMAN_APPROVAL_REQUIRED: YES — decidir arquitetura; publicação/teste manual e schedule exigem autorizações posteriores separadas
```

**Recomendação para decisão humana:** adotar B como arquitetura preferida e avançar somente para preparação da validação manual, sem schedule. Nenhum workflow foi disparado ou publicado; aguardar decisão humana.
