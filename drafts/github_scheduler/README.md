# SCHEDULER_ARCHITECTURE_DECISION — proposta, pendente de aprovação

**Recomendação: alternativa B, relógio GitHub separado na main, dispatch para dev.**
Status YELLOW para implantação: configuração viável, rascunho/testes preparados,
mas sem aprovação arquitetural, teste real do novo token ou frequência de clientes.
Não abandonar oficialmente Supabase Cron: seus rascunhos e evidências permanecem
intactos. automation_remote_runner_validated e probe transacional continuam GREEN.

## Preflight real, somente leitura — 19/10/2026

Repositório DungeonCodes/sheets-supabase-sync, público, não arquivado/desabilitado.
Branch local dev, HEAD local/remoto 00a06ecc8e3fb758351d4a14e6c991a6dd370b14;
worktree inicialmente limpa. Branch padrão main. GitHub Actions habilitado,
allowed_actions=all; workflow staging-dispatch ativo, ID 388468858.
scheduled-sync.yml existe em main e dev e é idêntico ao local:
blob Git 65d16e28a9e00918a0eac2213ab57b0e73fc6ea0.

Environment staging com custom_branch_policies=true, protected_branches=false;
uma única política: **branch dev**, nenhuma regra de tag. Sete secrets presentes
somente por nome: APP_ENV, SUPABASE_PROJECT_REF, SUPABASE_ALLOWED_PROJECT_REF,
SUPABASE_URL, SUPABASE_DB_URL, GOOGLE_SERVICE_ACCOUNT_JSON, STAGING_SYNC_CONFIG_JSON.
Nenhum valor lido ou alterado. Zero variáveis de repositório atualmente cadastradas.
Nenhuma consulta ao Supabase/Google; baseline 9/11/8 é somente contexto anterior.

## Matriz comparativa

| Critério | A — Supabase Cron → pg_net → Edge → GitHub | B — GitHub clock main → workflow_dispatch dev |
| --- | --- | --- |
| Viabilidade atual | YELLOW: prova de origem Cron não resolvida | Configuração/documentação permitem; permissão emitida e handoff real ainda precisam de teste autorizado |
| Autenticação | Exige nova fronteira de identidade confiável fora da fila | Identidade nativa do job; GITHUB_TOKEN temporário do próprio repositório |
| Credenciais adicionais | PAT GitHub, identidade SQL Edge e eventual ingresso; nenhum criado | Nenhuma credencial cadastrada; token automático do job |
| Segredos de dados | PAT/DB/ingresso exigem stores e fronteiras de confiança | Relógio sem environment e sem secrets Supabase/Google; só destino dev usa staging |
| Superfície | Fila legível, endpoint HTTP, código Edge, ACL/owner/roles | Workflow main e job com Actions:write; sem endpoint público adicional |
| Componentes novos | Extensões, job, funções, deploy Edge, autenticação | Um workflow separado, sem alterar Python/destino |
| Confiabilidade | Depende de disponibilidade DB, fila, Edge, GitHub e origem segura | Menos componentes; schedule pode atrasar/perder ticks, sem SLA de horário |
| Concorrência/duplicidade | Claim persistida ajuda, mas ingresso permanece pendente | Concurrency existente serializa destino; não é deduplicação durável nem exactly-once |
| Observabilidade | Correlacionar autorização/job/fila/Edge/run/reconciliação | Clock run_id → retorno API target run_id → job/deployment/dispatcher/reconciliação |
| Custos | Recursos DB/Edge/egress e manutenção de credenciais; custo marginal não medido | Runner padrão gratuito no repositório público; ainda há quotas/limites e recursos de logs/armazenamento |
| Manutenção | Mais código, grants, segredo/rotação, versões e incidentes possíveis | Relógio pequeno, políticas/retention/inatividade e revisão de permissões |
| Horário exato | Não demonstrado pela integração atual; DB também não garante cadeia inteira | Sem garantia; inadequado se cliente exigir pontualidade rígida/intervalos inferiores ao mínimo suportado |
| Rollback | Desativar todas as peças com estado auditável | Desabilitar só clock; destino manual permanece disponível |

Conclusão: B resolve a necessidade de agendamento sem introduzir o problema de
prova de origem HTTP da alternativa A. A seleção é uma **proposta humana**, não
uma declaração de abandono da alternativa A ou autorização de implantação.

## Permissões reais e limites de confirmação

GET actions/permissions/workflow retornou default_workflow_permissions=read e
can_approve_pull_request_reviews=false. O destino existente declara somente
contents:read; com essa declaração, Actions não recebe write. Ele não precisa
de write para executar Python e não será alterado para concedê-lo.

O relógio declara permissions:{} no topo e, apenas no job clock:
**actions:write + contents:read**. Actions:write permite dispatch no mesmo repo;
contents:read é usado para consultar a revisão de dev. Os demais privilégios
declarativos ficam none. Defaults read podem ser ajustados pelo permissions do
job; o relógio só admite schedule/workflow_dispatch na main, não PR/fork.
Eventos workflow_dispatch são exceção à supressão usual de novos workflows
por GITHUB_TOKEN. Não é necessário PAT/GitHub App ou alterar defaults globais.

GITHUB_TOKEN é emitido automaticamente para o job e expira; não está disponível
nesta sessão como token do relógio inexistente. A credencial gh usada para GETs
de governança **não comprova** as permissões do futuro GITHUB_TOKEN. Portanto,
estão confirmadas a configuração atual e a viabilidade documentada; falta
comprovar o token efetivamente emitido e a resposta do dispatch no novo teste.
Se uma política da plataforma impedir write, parar; não criar PAT de fallback.

Actions:write é amplo para Actions deste repositório, não restrito ao workflow
scheduled-sync.yml. O código fixa destino e não concede contents:write, mas
quem puder alterar o relógio/main pode abusar do token. Revisar permissões de
colaboradores e proteção/revisão da main antes de ativar; não assumir proteção
de branch que não foi auditada neste gate. Não usar código de PR no job clock.

## YAML e comportamento preparado

[staging-clock.draft.yml](staging-clock.draft.yml) fica apenas em drafts/. Não é
um workflow registrado. Tem só workflow_dispatch para um **futuro teste controlado**;
não contém schedule nem expressão cron. Frequência definitiva permanece TBD.
Código para evento schedule está testado, mas esse evento não está habilitado.

O rascunho não faz checkout e não usa action de terceiro. Token automático é
referenciado por github.token, nunca recebe secrets de dados ou environment.
Um job único de até três minutos, group staging-clock, cancel-in-progress=false.
Nunca usar o grupo do destino no relógio: manter o pai segurando o lock do filho
enquanto o observa pode bloquear o handoff. Python continua exclusivamente no
workflow atual em dev/environment staging.

Travas antes do POST: repositório correto, refs/heads/main, evento permitido,
run_attempt=1, STAGING_CLOCK_ENABLED=true, confirmação manual, SHA de dev aprovado,
workflow destino ativo e janela de aprovação ainda válida. A janela de até
15 minutos é **trava do teste**, não frequência ou SLA de cliente. A variável
opt-in não existe hoje, portanto publicação isolada não habilita disparo.
Em futuro schedule, SHA/janela vêm das variáveis documentadas no YAML; a política
dessas aprovações para operação contínua terá de ser revista depois dos clientes.

Relógio verifica lista paginada de runs dev, até dez páginas. Se houver queued,
in_progress, waiting, pending ou requested, retorna busy_skip sem dispatch. Se
não estabelecer o estado dentro do limite, bloqueia. Consulta não é lock atômico:
um disparo manual pode entrar depois dela. O destino continua protegendo a
execução com seu próprio grupo staging-dispatch-refs/heads/dev.

Uma única tentativa POST oficial, ref dev e return_run_details=true; nenhum
input novo enviado ao destino existente. Timeout por HTTP de dez segundos,
redirect:error, zero retries, inclusive GETs não têm loop de retry. Paginação
é leitura de páginas distintas. Rerun do relógio (attempt>1) é recusado.

HTTP 200 só é aceito com run_id e URLs oficiais consistentes. GET seguinte
confere workflow_id, event=workflow_dispatch, head_branch=dev, SHA esperado e
attempt=1. Logs são JSONs limitados a IDs, URL pública, SHA e categorias locais;
nenhum header, corpo HTTP, token ou erro bruto. `dispatch_accepted_not_completed`
não atesta environment/guard/Python/conclusão; esses são verificados no destino.

### Concorrência, perdas e retries

O destino existente permite uma execução ativa e uma pendente por grupo;
nova chegada pode cancelar/substituir a pendente, mesmo com cancel-in-progress=false.
O relógio reduz chegadas enquanto ocupado, mas não garante ausência de corrida
com humanos nem entrega de cada tick. queue:max é opção documentada para revisão
futura se clientes exigirem backlog; não foi adicionada ao destino neste gate.
Não trocar por uma fila maior sem requisito: pode apenas acumular trabalho velho.

Concurrency não deduplica. Dois novos runs manuais do relógio são duas decisões
distintas, e o controle run_attempt não os une. Não afirmar autorização global
de uso único ou exactly-once. Idempotência/locks do dispatcher continuam defesa
do domínio; não são garantia de que apenas um workflow/run auditável será criado.

Timeout, 204, resposta inválida ou observação perdida após POST são ambíguos.
Não reenviar, não usar gh workflow run para recuperar automaticamente, não
habilitar rerun como retry. Consultar GitHub primeiro. Se o run_id foi recebido,
investigar somente ele. Se foi perdido, buscar candidatos por janela/ref/SHA/
ator e comparar estado antes/depois; havendo concorrência, a correlação pode
continuar inconclusiva. O destino atual não recebe correlation_id do relógio;
não inventar correlação exata nessa situação. Inputs/título seriam uma melhoria
futura separada se rastreabilidade rígida for requisito.

O SHA é conferido antes e depois do POST, mas ref dev continua móvel. Sem alterar
o destino, isso detecta divergência depois de criar a run, não impede Python de
iniciar com outra revisão. **Congelar dev na janela controlada**. Pin estrito
antes do Python exige guard adicional no destino, que não foi alterado aqui.

## Schedule e requisitos pendentes

Schedule executa apenas a versão da branch padrão main. GitHub documenta atraso
sob carga e possível perda de jobs; public repos têm desativação após 60 dias sem
atividade. O menor intervalo documentado é cinco minutos; isso é limite técnico,
não proposta de frequência. Evitar o começo da hora quando definir cron. Definir
timezone/UTC conscientemente; a documentação também suporta timezone IANA.
Nenhum horário, frequência, recuperação de backlog ou SLA foi escolhido agora.

Confirmar com clientes: frequência por fonte, tolerância a atraso/perda, horários
comerciais/timezone, volume/duração, prioridades, backlog, monitoramento e quem
atende falha/inatividade. Intervalo configurado no dispatcher é independente do
tick do relógio: um tick pode selecionar zero fontes due, sem equivaler a erro.
Não presumir que source de demonstração representa a frequência dos clientes.

## Ativação controlada — não executar neste gate

1. Aprovar ADR proposta e confirmar que B será experimentada; A fica preservada.
2. Revisar/publicar humanamente apenas o relógio em main, **sem schedule**, com
   opt-in ausente/false. Manter scheduled-sync.yml/Python e environment dev-only.
   Publicação/commit/push não são executados pelo agente. Conferir diff e políticas.
3. Autorizar separadamente UM teste do relógio, que poderá iniciar UMA sincronização
   real em staging. Atualizar baseline READ ONLY e dry-selection pelo fluxo já
   autorizado nesse futuro gate; não reabrir os testes remotos antigos agora.
4. Congelar dev, verificar SHA/nenhuma execução concorrente/environment/secrets;
   habilitar apenas STAGING_CLOCK_ENABLED e usar inputs SHA, confirmação true e
   expiry UTC curta. Não criar secrets, PAT ou token manual. Operador acompanha.
5. Iniciar uma vez o relógio em main. Conferir permissões efetivamente emitidas
   no setup do job (Actions:write/Contents:read) de forma sanitizada. Não aprovar
   somente porque o token gh local tem acesso. Se falhar/timeout, não repetir.
6. Registrar parent run_id e child run_id. Validar event/ref/SHA, deployment
   staging, runner GitHub-hosted, guard, Python, dispatcher e contadores/status
   individuais. Reconciliar Supabase READ ONLY com baseline; no_changes é válido.
7. Desabilitar opt-in imediatamente ao terminar ou abortar, preservar logs e
   confirmar ausência de nova execução. Clock aceito não é sincronização concluída.
8. Só depois de requisitos dos clientes e nova aprovação adicionar schedule
   escolhido e política operacional de enable/SHA/expiração. A janela de teste
   deste draft não é desenho definitivo de recorrência. Primeiro tick schedule
   terá de ser observado para provar evento schedule real; manual não o comprova.

## Rollback e observabilidade

Plano futuro: colocar STAGING_CLOCK_ENABLED=false e desabilitar **apenas staging-clock**
na UI; depois remover schedule quando houver, por mudança humana revisada. Conferir
ticks/runs já enfileirados. Essas ações não desfazem POST aceito. Não desabilitar
staging-dispatch nem revogar/alterar as sete secrets para parar o relógio.
Não cancelar uma sync durante commit como forma de rollback; acompanhar e reconciliar
o run existente. Tentativa manual ambígua nunca é compensada por novo dispatch.

Manter histórico clock→child, status busy_skip/ambiguidade, última conclusão do
dispatcher e idade desde último sucesso. Definir alerta/responsável antes de
recorrência; um schedule que não criou run não oferece log de falha. Não usar
commits artificiais para contornar inatividade. Conferir retenção configurada;
logs expiram e não substituem trilha sanitizada durável. Nenhum monitor foi implantado.

## Testes, custos e limites de evidência

32 testes Node offline executam **o JavaScript extraído do próprio YAML**, sem
copiar sua implementação. Fetch/process/clock/log são injetados; nenhuma chamada
real. Cobrem contexto/fork/ref/rerun, opt-in/confirmação/expiração, SHA, busy,
paginação, payload fixo, falhas/timeout/redirect/204/200 ambíguo e correlação.
Teste não emite GITHUB_TOKEN, não valida runner hospedado nem substitui validação
do YAML pelo GitHub. Nenhuma dependência de parser/produção instalada.

```powershell
node --test tests/cron_dispatch/github-clock.test.mjs
```

O repo público com ubuntu-latest padrão se enquadra na gratuidade documentada
de execução de runner; não se contratou serviço ou alterou plano. Custos de
armazenamento, quotas, runners especiais e mudança de visibilidade exigem
reavaliação. Sem frequência/tempo por cliente, não estimar custo mensal nem
garantir custo total zero. A mantém consumo adicional DB/Edge/egress e manutenção
de credenciais, sem nova consulta de faturamento ou implantação para medi-lo.

Nenhum arquivo .github/workflows, código Python, SQL ou rascunho Supabase foi
alterado. Nenhum workflow, schedule, deploy, token, secret, migration, produção,
commit ou push executado. Próxima aprovação: **APROVAR ADR PROPOSTA DE RELÓGIO
GITHUB ACTIONS**, sem ativação, abandono de A ou dispatch implícitos.

## Fontes oficiais verificadas em 19/10/2026

- [GITHUB_TOKEN e exceção workflow_dispatch](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
- [Permissões do job e cálculo efetivo](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions)
- [REST workflow dispatch / Actions:write](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
- [Schedule, atraso, perda e inatividade](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Concorrência e fila pendente](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- [Validade do token automático](https://docs.github.com/en/actions/concepts/security/github_token)
- [Custos Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
