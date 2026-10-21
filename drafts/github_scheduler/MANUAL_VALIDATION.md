# GITHUB_CLOCK_MANUAL_VALIDATION_PREPARATION

20/10/2026. **GREEN para preparação offline; publicação e execução NÃO autorizadas.**
Decisão humana: B aprovada como arquitetura candidata principal. Nenhuma aprovação
de schedule, frequência, publicação ou dispatch pode ser inferida dessa decisão.

## Preflight observado

Host DESKTOP-VU6VMS6; raiz C:/Users/tisap/Documents/GitHub/sheets-supabase-sync;
branch dev, HEAD b84f1b2eeca0f9ffe3fa135ba03f2468eb3928e9. Origin/dev coincide
por ls-remote; origin/main 88ae3008140905ce05a4fcf7c01bc6db72db6c78. Sem fetch.
Alterações iniciais preservadas: docs/decisions.md, docs/run_log.md e os três
arquivos novos da proposta anterior (ADR de 20/10, draft v2 e seu teste).

GitHub GET: main padrão, público, Actions habilitado; permissões padrão read,
allowed_actions all, sha_pinning_required false. Lista paginada de workflows:
somente offline-checks/ci.yml e staging-dispatch/scheduled-sync.yml, ambos ativos.
Arquivos completos remotos main/dev inspecionados: CI push/pull_request sem
dispatch emissor, executor apenas workflow_dispatch sem schedule. Nenhum relógio
equivalente registrado ou presente nessas duas branches; não é prova sobre
acionadores externos desconhecidos. Repetir inventário imediatamente antes da
publicação/teste. Não publicar dois drafts com nomes diferentes.

Staging tem custom_branch_policies=true e única regra branch dev, nenhuma tag;
sem required reviewers retornados, can_admins_bypass=true. Sete environment
secrets conferidas só por nomes, sem valores. Nenhuma repository variable
configurada: opt-in e autorização do draft ainda inexistem. Executor main/dev
tem blob 65d16e28a9e00918a0eac2213ab57b0e73fc6ea0; sem alteração local.
APP_ENV/refs secretos não foram lidos; guard runtime e gate anterior são as
evidências de valor, não os metadados do GitHub. Run GREEN 39247320871 e probe
transacional continuam evidências anteriores, sem repetir suas execuções.

## Revisão integral do v2 e candidato manual

V2 foi lido integralmente e preservado com testes históricos. A revisão revelou:

- Um POST por run e recusa de rerun não bloqueavam uma segunda run manual nova
  usando a mesma janela. Concurrency só serializa; não consome autorização.
- Faltava registro sanitizado anterior ao POST, horários e classificação HTTP.
- Aceitação não coletava contadores/conclusão financeira do filho; exit code 0
  do batch_cli pode coexistir com sources_failed>0.
- V2 permitia evento schedule no código, embora sem gatilho YAML. O candidato
  desta etapa será estritamente manual, sem fallback para variáveis de schedule.

Candidato revisado: [staging-clock-manual.draft.yml](staging-clock-manual.draft.yml).
Único destino de publicação futura: `.github/workflows/staging-clock.yml`, main.
Não publicar v1/v2 junto; são histórico. Nenhum arquivo foi colocado em workflows.

Inputs: confirmação booleana default false, expected_dev_sha e expiração UTC até
15 minutos. Nunca receber repository/workflow/ref por input. Constantes:
DungeonCodes/sheets-supabase-sync, scheduled-sync.yml, dev. Validar origem
refs/heads/main, workflow_ref exato do arquivo de publicação, evento manual,
attempt=1, GITHUB_RUN_ID, SHA dev revisado, target ativo e revisão ainda igual.
Freeze de dev durante teste continua necessário: ref móvel pode avançar entre
preflight e dispatch e verificação posterior não impede execução divergente.

Permissões: topo vazio; só job clock com **actions:write + contents:read**.
Contents:read é necessária ao GET git/ref/heads/dev para conferir revisão.
Actions:write não é restrita ao único workflow; permite outras operações Actions,
inclusive dispatch/rerun/cancelamento conforme endpoint. Código fixa alvo e só
usa leituras + único POST de dispatch. Não há privilégio de editar conteúdos,
ler valores de secrets ou administrar environment por essa permissão. Mudança
maliciosa do código por escritor autorizado permanece risco; revisar acesso e
proteções de branch, sem presumir controles não auditados.

Clock sem environment, secrets de dados, checkout, action terceira, pip/Python
ou credenciais Google/Supabase. Somente github.token temporário; nenhum PAT.
Proteção staging é **por branch, não por identidade de workflow**: outro job
autorizado na dev que referencie staging pode ter acesso às mesmas secrets.
Main tentando usar staging é bloqueada pela política atual; administradores
que alterem política/código são parte da fronteira de confiança.

Timeout job 3 minutos, HTTP 10s, redirect recusado. Grupo staging-clock distinto
de staging-dispatch-refs/heads/dev; cancel-in-progress=false nos dois. Busy scan
paginado de queued/in_progress/waiting/pending/requested, até dez páginas; se
inconclusivo bloqueia. Busy conhecido vira skip, não autorização para retry.
Executor mantém elegibilidade por fonte, intervalo, locks e staging guard atuais.

## Uma autorização para uma run do relógio

Futuro teste B requer duas repository variables não secretas, **não criadas aqui**:

- STAGING_CLOCK_ENABLED=true somente durante janela autorizada;
- STAGING_CLOCK_AUTHORIZED_RUN_NUMBER igual ao número exato da próxima run
  manual desse único workflow, revisado pelo humano.

O job exige GITHUB_RUN_NUMBER igual ao número autorizado e run_attempt=1.
Nova run tem outro número e bloqueia; rerun também bloqueia. Publicação A deixa
essas variáveis ausentes: não provoca sync mesmo se alguém acionar o manual.
Calcular número esperado consultando runs do workflow; em workflow novo sem
histórico confirmar início esperado da numeração. Se houver disputa e a run
autorizada for consumida por tentativa bloqueada/skip/falha, parar; não avançar
variável, não executar outra run sem nova autorização humana. Congelar o único
workflow e não apagar/recriar sua identidade durante teste.

Esse vínculo não é ledger transacional/exactly-once. Depende da identidade estável
do workflow, variáveis sob controle humano e código revisado. Não impede dispatch
direto por outros atores, corrida com acionamento manual do executor ou criação
de workflow alternativo por escritor autorizado. O teste pode criar no máximo
um POST nesse caminho/autoridade; não garantir uma única sync global.

Sem retry automático de GET/POST, rerun, fallback PAT ou compensação. Retries
transacionais seguros já existentes no domínio Python não são alterados.

## HTTP, correlação e resultado

Referência oficial atual para versão REST **2026-03-10** documenta body ref/inputs
e resposta **200 com workflow_run_id/run_url/html_url**. `return_run_details` foi
avaliado, mas não está listado como parâmetro no contrato atual consultado;
não enviá-lo no candidato. Draft v1 preserva o estudo anterior. Se API devolver
204, campo ausente, JSON inválido ou timeout, tratar como ambiguidade e consultar
GitHub antes de qualquer tentativa. Não fazer fallback de versão/API/POST.

Antes da chamada: registro dispatch_attempt_started com clock_run_id, run_number,
clock_sha, expected_dev_sha, main/dev e timestamp UTC. Depois: status HTTP seguro
e IDs/URLs validados; GET do filho verifica workflow_id/event/branch/SHA/attempt.
401/403 = AUTHORIZATION_DENIED; POST 404/422 = DISPATCH_REJECTED. 429/5xx e
transportes/repostas incompletas após tentativa ficam bloqueados/ambíguos; nenhum
retry. GET de observação falho mantém executor_run_id conhecido. Não registrar
headers, corpo bruto, token nem mensagem arbitrária de erro.

`dispatch_accepted_not_completed` significa apenas aceitação/identidade, mesmo
que o job clock finalize com código zero. Não aguarda ou declara GREEN do filho.
Timeout total pode cortar último log: registro pré-POST indica tentativa possível,
não entrega garantida. Se perder run_id, buscar candidatos por workflow/ref/SHA/
janela/ator; sem correlação inequívoca, manter UNKNOWN e reconciliar, sem replay.
IDs GitHub não são automaticamente os UUIDs sync_runs do PostgreSQL.

Preparado [executor-observation.mjs](executor-observation.mjs), função pura offline
sem rede/fs/token, para classificar metadados e resumo reais posteriormente. Não
instalada no executor/clock. Caller fornece **resumo JSON do step correto**, não
logs completos ou dados da planilha; mantém somente allowlist de IDs, branch/SHA,
horários, conclusão e contadores. Conferir origem do resumo manualmente; uma
função offline não autentica a proveniência da entrada.

Captura prevista na etapa C (nenhuma evidência real nova criada neste gate):

| Campo | Origem / limite |
|---|---|
| clock_run_id / run_number / SHA main | execução autorizada e registro pré-POST |
| executor_run_id / SHA dev / workflow_id | resposta validada + GET do filho |
| created_at / updated_at / checked_at | metadados GitHub e observação UTC |
| http_status / código de falha | resposta allowlisted; nunca corpo de erro |
| conclusão do executor | GET completed + conclusion; sucesso necessário, insuficiente |
| sources_total/due/executed/no_changes/skipped/failed/busy_deferred | resumo JSON único do step Dispatch due staging sources |
| staging_guard_verified | conferência do step guard e configuração de destino, sem valores secretos |
| reconciliation_verified | leitura humana autorizada do staging, corte/source/run coerentes |

Classificação: PENDING, IDENTITY_MISMATCH, EXECUTOR_NOT_SUCCESSFUL, SUMMARY_INVALID,
COUNTERS_INCONSISTENT, SOURCES_FAILED, BUSY_DEFERRED ou AWAITING_STAGING_RECONCILIATION.
Só GREEN com sucesso/identidade, resumo válido, sources_failed=0, busy=0, guard
e reconciliação conferidos e datas válidas. Zero due é NO_DUE_SOURCES válido,
não fingir sync executada. Contadores ausentes não são zero. sources_failed>0
em resumo válido com exit code/GitHub success é explicitamente SOURCES_FAILED.
Falha do próprio workflow já impede GREEN mesmo sem resumo. Inspecionar também
jobs/steps quando environment ou secrets bloquearem a execução.

## Plano controlado — nenhuma etapa executada

**A — publicação manual somente, próximo gate.** Aprovação específica:
APROVAR PUBLICAÇÃO MANUAL DO RELÓGIO NA MAIN. Revisar candidato, paths fixos,
SHA e permissões, inventário de relógios e stage policy. Publicação por humano,
somente este arquivo como staging-clock.yml na main, sem schedule e sem criar
variables de enable/autorização. Não alterar scheduled-sync.yml. Verificar diff
de main e registro do workflow sem executá-lo. Gates GREEN não são reabertos.

**B — uma chamada manual, outra aprovação.** Repetir inventário/ausência de
schedule, token policy, dev SHA e freeze; garantir executor ocioso; obter
baseline atual de staging somente por leitor autorizado em gate específico.
Registrar autorização da run_number e janela, preparar inputs e variables
somente com aprovação correspondente. Não inferir essa autorização de A.
Acionar uma vez workflow main; observar registros de tentativa e ID filho.
Qualquer falha/busy/timeout/ambiguidade encerra a autorização; investigar sem
retry, retirar opt-in quando seguro. Teste com token realmente emitido ainda
pendente; gh local e mocks não o comprovam.

**C — observação e reconciliação, no teste aprovado.** Acompanhar filho até
terminal; validar dev/SHA/attempt e environment, guard, cleanup e resumo.
Usar função offline com contadores conferidos, sem resumir GitHub success como
sucesso de fontes. Revisar staging por procedimentos de leitura autorizados,
sem migrations/SQL de escrita. Comparar baseline nova com resultado esperado,
inclusive zero mudanças e busy; não exigir 9/11/8 antigo como baseline atual.
Como executor não emite IDs GitHub no PostgreSQL e resumo não traz UUID por sync,
correlacionar com janela/source e ausência de concorrência; se insuficiente,
registrar inconclusivo, sem inventar vínculo ou alterar executor neste gate.

**D — schedule, nova decisão posterior.** Escolher frequência só após requisitos,
observador independente para ticks perdidos, tolerância/SLA, custo/volume e
resposta à inatividade. Este candidato recusa evento schedule; etapa D exige
revisão própria de código e política de autorização recorrente, não apenas
acrescentar cron ao YAML manual. Nenhum horário escolhido.

Rollback: antes de B, remover opt-in/authorized run number e desabilitar apenas
clock; em A ainda sem variáveis, manter workflow inerte ou removê-lo por mudança
humana revisada. Disabling não desfaz POST aceito: verificar parent/child e
acompanhar sync em curso, não cancelar commit nem disparar compensação. Preservar
executor manual, environment, sete secrets, históricos e rascunhos Cron/Edge.

## Testes offline e limites

150 testes PASS: 50 clock manual + 27 classificação de observação + 32 v1 +
34 v2 + 7 dispatcher Python. Históricos intactos. Cobertura inclui evento/ref/
workflow path fixo, run_number, rerun, autorização, token insuficiente 401/403,
timeout/ambiguidade/HTTP, busy/paginação, pré-registro, payload fixo, correlação,
ausência de secrets/schedule e contadores com falha apesar de exit code zero.

Parser PyYAML **6.0.3 já disponível no Python do sistema**, BaseLoader para manter
chave on textual: sintaxe e estrutura do candidato PASS. Nenhuma dependência
instalada ou adicionada; Python de produção não alterado. Parser não verifica
toda a semântica do GitHub nem permissões emitidas. Programa JavaScript exato
extraído do YAML executado apenas com fetch/clock/process/log simulados. Testes
Python existentes usam dependências simuladas. Nenhuma execução real/SQL/benchmark.

Comandos offline executados:

```text
node --test tests/cron_dispatch/github-clock-manual.test.mjs tests/cron_dispatch/executor-observation.test.mjs tests/cron_dispatch/github-clock.test.mjs tests/cron_dispatch/github-clock-v2.test.mjs
.venv/Scripts/python.exe -m unittest tests.unit.test_dispatcher -v
```

## Fontes oficiais reconferidas em 20/10/2026

- [REST dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event): Actions:write, ref e retorno atual HTTP 200/run ID.
- [Token do job](https://docs.github.com/en/actions/concepts/security/github_token): temporário, repositório atual, exceção workflow_dispatch.
- [Permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions): permissões explícitas por job; sem privilégio padrão de escrita presumido.
- [Environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments): branch policy e disponibilidade de secrets para jobs que declaram environment.

## Relatório final

```text
STATUS: GREEN (preparação offline; nenhum handoff real validado)
ARCHITECTURE: GITHUB_ACTIONS_CLOCK
CLOCK_WORKFLOW_READY: YES (candidato manual revisável, não publicado)
SCHEDULE_ENABLED: NO
TARGET_BRANCH: dev
STAGING_GUARD: PRESERVED; executor/APP_ENV/refs/environment sem mudanças
GITHUB_TOKEN_PERMISSIONS: actions:write + contents:read no job; topo vazio
SECURITY: alvo fixo, main/path/event manual, sem secrets de dados/PAT; staging é branch-only
DUPLICATE_PROTECTION: número autorizado + attempt 1 + um POST + busy/concurrency + locks; não exactly-once
CORRELATION: tentativa pré-POST, HTTP/IDs/SHA/horários + observação do filho e contadores; perda de resposta exige inspeção
TEST_RESULTS: 150 PASS + parser YAML/estrutura PASS
FILES_MODIFIED: candidato manual, helper offline, dois testes novos, este plano; ADR/índice/run_log com registro adicional
PUBLISHING_PLAN: A publicar manual inerte; B teste único autorizado; C observar/reconciliar staging; D aprovação própria de schedule
ROLLBACK: desabilitar só clock/opt-in, acompanhar filhos aceitos, preservar executor/secrets
RISK: token amplo; ref móvel; concorrência externa; ausência de correlação DB direta; mocks não provam token real
NEXT_GATE: GITHUB_CLOCK_MANUAL_PUBLICATION
HUMAN_APPROVAL_REQUIRED: APROVAR PUBLICAÇÃO MANUAL DO RELÓGIO NA MAIN
```

Nenhuma etapa A–D executada. Aguardar autorização humana somente para publicação
manual inerte; essa aprovação futura não autoriza dispatch.
