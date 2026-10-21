# GITHUB_CLOCK_SCHEDULE_PUBLICATION_PREPARATION — 2026-10-21

STATUS: YELLOW
MANUAL_MODE_PRESERVED: YES
SCHEDULED_MODE_READY: YES — candidato offline para revisao; NAO autorizado para publicar/ativar
PROPOSED_PILOT_INTERVAL: 60_MINUTES
PILOT_INTERVAL_APPROVED: NO
REVISION_POLICY: SHA aprovado explicitamente, atualizado apenas por aprovacao humana
ALERT_OWNER: PENDING
NEXT_GATE: GITHUB_CLOCK_SCHEDULE_PUBLICATION_REVIEW

Este relatorio complementa README.md (gate anterior), sem apagar seu historico.
Preparo tecnico concluido e testado; YELLOW reflete governanca de dev, aprovacao de
SLA/cadencia e responsavel/rotina de silencio ainda pendentes. Nao ha cron ativo no
candidato, nem recorrencia publicada. Prontidao aqui significa artefato revisavel.

## Preflight renovado

Repositorio DungeonCodes/sheets-supabase-sync, publico, default main, host
DESKTOP-JJA98HA. Branch local dev; HEAD 14b6672908fddf688905d8a96d66e78d78b9851d.
Origin configurado para esse repositorio. API e git ls-remote confirmaram:
main/origin-main 80cdde4bb79506deecb3d37f0e9894fba03739ac;
dev/origin-dev 294dceb07ad131a0b45f84b79b611b126e0e9558.
HEAD e ancestral de origin/dev, 0 commits a frente/8 atras. Nao houve fetch/pull,
checkout, merge ou atualizacao de refs. protected=false nas duas branches; nao se
presume regras de revisao obrigatoria sem auditoria de rulesets no gate de revisao.
Repository variables continuam vazias. API contents leu clock atual main e executor
atual dev, preservados em main-clock-reviewed.yml/dev-executor-reviewed.yml. Clock
manual baseline coincide com o publicado; executor operacional local coincide com
o publicado. batch_cli.py atual dev tambem foi inspecionado e coincide com a base
do patch isolado. Nenhum SHA antigo foi usado como autorizacao futura.

Alteracoes locais preexistentes: docs/decisions.md, docs/run_log.md, ADR readiness e
drafts/. Preservadas; candidatos e testes anteriores guardados em *.readiness-v1;
manual-baseline.yml permanece intocado. Workflows operacionais e src nao mudaram.
Nao consultados dados/credenciais de staging, nem repetidos testes remotos GREEN.

## Revisao aprovada e corrida

STAGING_CLOCK_APPROVED_DEV_SHA: SHA completo aprovado por humano, sem atualizacao
automatica. STAGING_CLOCK_SCHEDULE_ENABLED: somente literal true habilita; ausente,
vazio, false ou outra grafia bloqueiam. Nenhuma variavel criada neste gate.

Clock scheduled verifica main/repo/workflow fixos, tentativa 1, opt-in e SHA aprovado;
consulta dev duas vezes, workflow ativo correto e runs concorrentes antes do POST.
Divergencia bloqueia com codigo local sanitizado; nao imprime resposta API bruta.
Payload scheduled fixo: ref dev e inputs execution_mode=scheduled, approved_dev_sha
validado e clock_run_id numerico. Manual continua POST {ref:dev}, com todos os
controles anteriores: confirmacao, numero autorizado, habilitacao manual, SHA
esperado, janela <=15min, identidade do filho e sem rerun/retry.

Executor candidato declara esses inputs com default manual para compatibilidade.
Seu PRIMEIRO passo, antes de checkout/install/materializacao de credenciais, valida
identidade fixa repo/dev/workflow_dispatch/workflow_ref e, em scheduled:
opt-in true, tentativa 1, SHA aprovado valido, input SHA == variavel aprovada ==
github.sha efetivamente executado, clock_run_id valido. Divergencia termina em falha,
sem rodar etapas seguintes. Checkout usa ref github.sha e verifica git HEAD antes
de instalar codigo; token de checkout nao persiste. Secrets continuam apenas na
etapa de materializacao existente. Clock nao recebe nenhum secret de staging.

SHA_RACE_MITIGATION: preflight nao e atomico com dispatch. Se dev mudar entre GET e
POST e a revisao filha conservar o guard, github.sha divergente bloqueia antes de
credenciais ou escrita; clock ainda verifica head_sha apos aceite. Se dev mudar
apos aceite, checkout permanece no SHA da execucao, nao segue a branch movel.
Variavel aprovada divergente ao iniciar filho tambem bloqueia. Snapshots de vars
nao sao revogacao instantanea para jobs ja iniciados.

Limite de confianca: workflow e guard residem na propria dev. Um commit que retire
o guard ou altere suas garantias nao e contido pelo guard antigo. Portanto publicar
o executor protegido primeiro, revisar seu SHA completo, controlar/fixar dev durante
o piloto e exigir revisao de toda mudanca de workflow e condicao para ativacao.
Branch protected=false impede declarar essa governanca ja implementada. Nao ha
pin atomico de workflow por SHA via ref dev, nem sandbox contra escritor autorizado
malicioso. Campos mode/clock_run_id sao correlacao, nao credenciais de autenticacao.
Execucao direta manual por mantenedor continua disponivel; nao deve ser usada para
contornar a politica recorrente. Nao adicionar PAT nem automatizar aprovacao.

## Correcao minima de sources_failed

SOURCES_FAILED_HANDLING: patch isolado batch_cli.sources_failed.patch troca somente
return 0 por return 1 if summary.sources_failed else 0, depois de emitir o mesmo
resumo. batch_cli.candidate.py e a copia executavel para testes, nao novo pipeline.
Nenhum arquivo src foi modificado e patch nao foi aplicado ao repositorio.

| Resultado | Exit CLI proposto | Tratamento |
| --- | ---: | --- |
| sucesso/applied ou no_changes | 0 | EXECUTOR_SUCCESS; nao confundir com nada devido |
| nenhuma fonte devida | 0 | CLOCK_SKIPPED_NO_DUE |
| busy deferred sem falha | 0 | CLOCK_BUSY, reconciliar se persistir |
| uma ou mais fontes falharam | 1 | EXECUTOR_PARTIAL_FAILURE, mesmo se todas falharem |
| erro de ambiente/estado/infraestrutura | 2 | EXECUTOR_FAILED |
| resumo ausente/invalido com exit zero | adapter 2 | EXECUTOR_UNKNOWN: falha de evidencia, nao afirmar sync falhou |

Processamento independente existente continua: fonte com falha nao impede a
seguinte. Resumo/evidencias e transacoes bem sucedidas sao preservados; nao ha
rollback global nem reexecucao automatica. Fonte invalida de selecao tambem conta
sources_failed. Sources_executed significa tentativas conforme dispatcher atual,
inclusive busy, e nao quantidade exclusivamente bem sucedida.

Executor candidato usa o mesmo run_cli, retendo resumo detalhado em memoria e
emitindo somente allowlist de agregados. Falha parcial com CLI legado exit zero
ja resulta em exit 1 pelo adapter (defesa adicional); nao depende de parsing de
logs brutos ou novo processo de sync. Logs Python internos ficam desabilitados
nesse processo publico; evidencia por source continua em staging e resumo completo
retornado pelo CLI continua disponivel fora do log publico. Nenhum artifact privado
ou payload bruto e publicado. A montagem de credenciais permanece efemera com cleanup.

Zero retries no clock, POST, workflow, wrapper e observador. Nao alterar politica
interna ja existente de retries/reconciliacao dos conectores/core neste gate: o core
local possui RetryPolicy limitada; isso nao e retry do clock nem redispatch.
Nao alegar zero tentativas internas end-to-end. Se o requisito futuro proibir tambem
retries internos, exige revisao especifica dessa politica, sem reabrir gate GREEN
por iniciativa automatica.

## Cadencia proposta e estimativas

Piloto proposto 60 minutos, ainda NAO aprovado. Nenhum cron adicionado. Propor offset
fora do inicio da hora, em UTC; minuto exato e tolerancia dependem da revisao.
E a frequencia do clock, nunca substitui sync_interval_minutes de cada source.

Caminho nominal por tick: GET workflow, GET dev, GET runs (uma pagina), GET dev,
POST dispatch e GET executor = 6 chamadas GitHub. Sem due nao e conhecido pelo clock:
filho precisa consultar dispatcher e pode concluir sem processar nenhuma source.
Busy: tipicamente 3 chamadas e nenhum POST. Opt-in off: zero chamadas API do programa.
Mais paginas aumentam ate 15 chamadas em caminho aceito (limite 10); falha de
paginacao bloqueia. Observador independente acrescentaria suas proprias leituras.

| Intervalo | Ticks/dia | Ticks/30d | GitHub requests nominais/30d | Runner-min ilustrativos/30d |
| --- | ---: | ---: | ---: | ---: |
| 15 min | 96 | 2880 | 17280 | 1488 |
| 30 min | 48 | 1440 | 8640 | 744 |
| 60 min proposto | 24 | 720 | 4320 | 372 |

Runner-min usa apenas janela anterior 10s clock +21s executor, sem arredondamento
ou novos overheads do guard/wrapper. Nao e benchmark, P95 nem estimativa de SLA.
Se, por hipotese ficticia, uma unica source vence a cada 180 min e sempre conclui,
sem outras fontes, ticks vazios/dia seriam 88/40/16 respectivamente (8 ticks com
source devida/dia). Intervalo real e dados de clientes nao foram lidos; sem inventario,
execucoes sem due podem variar de 0 a todos os ticks. No_changes tem due e leitura
Google, portanto nao conta como tick vazio.

Computacao GitHub em standard public runners: estimativa US$0, nao incluindo storage
ou servicos externos. Nao gerar artifacts novos. GitHub pode atrasar/descartar ticks;
periodo menor reduz atraso ideal, mas nao fornece garantia. 60 min implica ate ~60min
adicionais ideais apos due, MAIS fila/duracao/atrasos sem limite garantido. Falha nao
e repetida automaticamente; proximo tick normal reavalia elegibilidade.

Supabase Free: 720/1440/2880 selecoes de estado por mes (assumindo um filho/tick),
mais locks/leitura/escrita conforme fontes elegiveis. Historico/raw pode crescer com
syncs efetivas mesmo em no_changes; nao prever tamanho a partir de uma amostra.
Free publicado inclui 500MB DB, 5GB egress, CPU compartilhada; observar uso real em
piloto aprovado. Pode pausar por baixa atividade em janela de 7 dias; nao prometer
que ticks garantem manter projeto ativo. Nao criar heartbeat artificial para isso.
Google Sheets: zero leituras de planilha sem due; custo proporcional a execucoes
reais e requests por source, com limites tipicos 300 reads/min/projeto e 60/min/usuario/
projeto. Contagem diaria pequena nao garante ausencia de burst. Nao adicionar retry
automatico no clock para 429 nem benchmark. Custo API/DB exato depende de uso real.

Fontes oficiais consultadas em 2026-10-21:
[GitHub schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule),
[GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
[Google quotas](https://developers.google.com/workspace/sheets/api/limits),
[Supabase limites](https://supabase.com/docs/guides/platform/billing-on-supabase),
[Supabase pausa](https://supabase.com/docs/guides/platform/free-project-pausing).
Github publico desabilita schedule apos 60 dias sem atividade; branch padrao executa
schedule; ator desprovisionado tambem pode interromper. Nenhuma execucao pontual garantida.

## Observabilidade e silencio

Estados contratuais em observation.mjs, com testes:
CLOCK_DISABLED, CLOCK_SKIPPED_NO_DUE, CLOCK_BUSY, DISPATCH_ACCEPTED,
EXECUTOR_SUCCESS, EXECUTOR_PARTIAL_FAILURE, EXECUTOR_FAILED, EXECUTOR_UNKNOWN,
TICK_DELAYED, TICK_MISSING_OR_UNKNOWN.

Clock busy e executor busy compartilham estado, distinguidos pelo executor_run_id e
etapa. CLOCK_SKIPPED_NO_DUE so e conhecido apos selecao do filho, nao por preflight.
DISPATCH_ACCEPTED nunca significa sucesso. EXECUTOR_FAILED requer evidencia de falha
(exit/conclusion/guard); falta de resumo, cancelamento isolado ou resposta ambigua
sao UNKNOWN quanto ao resultado da sincronizacao. TICK_MISSING_OR_UNKNOWN nao prova
falha de dados. As funcoes assessExecution/assessTick anteriores ficam como modelo
legado; publicObservation/executorState definem o contrato atual, sem coletor paralelo.

Allowlist: mode, expected_at, actual_at, clock_run_id, executor_run_id, clock_sha,
executor_sha, sources_total, sources_due, sources_executed, sources_failed,
sources_busy_deferred, duration_seconds, last_success_at. Campos invalidos/desconhecidos
viram null, nunca zero inventado. expected_at permanece null ate escolher cron e
slot; event.schedule e expressao, nao timestamp nominal garantido. Horario real do
clock nos registros at; adapter atual_at e termino real do processamento; inicio do
run vem dos metadados GitHub. Duracao do adapter nao inclui fila/checkout/install.

Candidato registra IDs/SHA no guard e no clock, contagens/horarios/duracao no adapter;
reconciliacao por run_id junta registros (nao depende de proximidade de horarios).
last_success_at em resultado saudavel e seu termino; em falha/busy fica null.
Ultima execucao saudavel global requer leitura dos registros anteriores; nao ha
cache/estado persistente novo. Ultima aplicacao por source continua sync_runs em
staging, distinta de tick saudavel/no due. Nunca incluir nomes de alunos/source,
PII, linhas, secrets, DSNs ou respostas privadas em logs publicos. Excecoes cruas
nao sao serializadas pelo clock/guard/adapter.

Proposta minima de alertas, ainda NAO configurada: notificacoes nativas Actions de
falha no workflow do executor e clock, responsavel inscrito e recebimento validado
em gate futuro. CLI patch/adapter eliminam o falso sucesso por sources_failed>0.
Para timeout/cancelamento/ausencia de resumo, revisar run sem redispatch automatico.
Falhas consecutivas: proposta avisar na primeira comprovada, escalar na segunda
consecutiva; busy persistente e unknown pedem reconciliacao, nao afirmar perda.
Responsavel e destinatario: PENDING.

MISSED_TICK_DETECTION: proprio clock nao detecta seu silencio permanente.
Proposta proporcional ao piloto horario: operador independente verifica a cada 2h
DURANTE janela de piloto acordada: workflow active, opt-in esperado, ultimo tick,
ultimo executor reconciliado, ultimo resumo valido e ultima execucao saudavel.
Propor tolerancia de 30min para atraso; com 90min desde slot esperado sem evidencia,
classificar TICK_MISSING_OR_UNKNOWN, investigar UI/API/ator/inatividade. Estes prazos
NAO sao SLA aprovado. Checagem a cada 2h nao garante resposta em 90min; deteccao
pode ocorrer apenas na proxima checagem. Fora da janela nao ha cobertura prometida.
SLA 24x7 ou menor prazo exigira justificativa para monitor independente externo,
nao outro tick no mesmo clock. Nao criar infraestrutura ou notificacoes agora.

Ausencia prolongada de sync_runs: nao equivale a tick perdido. Operador compara
fontes ativas e devidas com ultima aplicacao valida e resumos, em consulta staging
somente leitura autorizada em gate futuro, sem valores de linhas. Fontes desabilitadas
ou sem due podem explicar ausencia; stale devido, erro de estado, pause/indisponibilidade
ou falta de evidencia exigem investigacao. Nenhuma consulta SQL neste gate.

## Plano de publicacao para revisao humana

1. Revisar os dois candidatos e patch contra refs renovadas; aplicar patch em branch
   revisada futura, sem usar checkout local atrasado como base de publicacao cega.
   Executar testes candidatos e atualizar regressao existente que espera exit zero
   com source failed (test_a_failing_source_does_not_prevent_the_next_due_source).
2. Aprovar governanca/congelamento de dev e politica de SHA explicito. Revisar todas
   as mudancas de workflow/core; manter sources, secrets e staging inalterados.
3. Publicar PRIMEIRO executor com guard/adapter e correcao CLI sob revisao especifica;
   manter opt-in ausente. Somente apos commit final revisado selecionar SHA de dev.
   O executor default manual segue funcional; validar manual em gate autorizado
   separado se necessario, nunca neste gate. Nao criar pipeline alternativo.
4. Publicar clock candidato em main sem schedule ativo enquanto cadencia nao aprovada.
   Confirmar manual preservado. Cron so entra por revisao humana posterior explicita;
   existencia de cron nao autoriza POST. Nao alterar default branch nem permissao
   staging para facilitar publicacao.
5. Antes de ativacao, revisar SHA real contendo guard e patch, aprovar intervalo,
   offset/timezone, tolerancia, janela de piloto, dono, alertas e rotina independente;
   registrar aprovador/UTC/SHAs/escopo/rollback em docs/decisions e docs/run_log.
6. Somente em gate autorizado configurar SHA aprovado e depois opt-in literal true.
   Confirmar valores por leitura, workflow active/main e dev SHA correspondente;
   nenhum numero manual serve de autorizacao recorrente. Observar primeiro tick,
   executor e evidencia agregada em gate posterior; nao declarar validacao remota aqui.

Criterios de ativacao: aprovacao de ambos workflows e patch; todos testes; dev
controlada com guard preservado; SHA final aprovado; cadencia/horarios aprovados;
responsavel nomeado e notificacao recebida; rotina independente aceita; limites
Free/Google observaveis; rollback revisado. Nenhum desses atos e executado agora.

## Rollback preparado

Remover STAGING_CLOCK_SCHEDULE_ENABLED ou definir false, sem alterar aprovacao manual.
Tests cobrem clock bloqueado e filho bloqueado por opt-in removido/false. Variavel e
snapshot: nao interrompe instantaneamente runs ja iniciados. Para emergencia,
desabilitar clock e reconciliar jobs queued/running; cancelar clock antes do POST
quando comprovavel. Nunca cancelar executor transacional cegamente nem reexecutar
POST ambiguo. Correlacionar todos IDs aceitos e confirmar resultado do filho.
Rollback de workflow: manter opt-in off, restaurar baseline manual via revisao;
restaurar executor anterior somente apos cessar recorrencia e reconciliar, pois o
anterior nao tem guard. Nao reverter dados nem apagar evidencias/sync_runs.
Reativacao exige nova aprovacao registrada; sem atualizacao automatica de SHA.

## Arquivos e testes

Novos/atualizados em drafts/github-clock-recurrence/: staging-clock.candidate.yml,
scheduled-sync.candidate.yml, batch_cli.sources_failed.patch, batch_cli.candidate.py,
main-clock-reviewed.yml, dev-executor-reviewed.yml, clock.test.mjs, executor.test.mjs,
observation.mjs, observation.test.mjs, test_publication.py, PUBLICATION_REVIEW.md.
Baseline manual e snapshots *.readiness-v1 preservados. Nenhuma dependencia nova.

Comandos offline:
node --test drafts/github-clock-recurrence/clock.test.mjs drafts/github-clock-recurrence/executor.test.mjs drafts/github-clock-recurrence/observation.test.mjs
.venv/Scripts/python.exe drafts/github-clock-recurrence/test_publication.py
.venv/Scripts/python.exe -m unittest tests.unit.test_dispatcher -v

Resultados: 59 testes Node, 12 Python candidatos/adapter, 7 Python existentes,
todos passaram. Programa JS do clock/guard e adapter Python extraidos dos candidatos
sao executados com fronteiras fake; sem GitHub/Supabase/Google durante os testes.
Correm modo manual autorizado/bloqueado, schedule mock/off, SHA aprovado/divergente,
corrida filha, concorrencia, partial failure, no_changes, busy, API indisponivel,
resposta ambigua sem retry, privacidade e rollback opt-in. Concurrency do GitHub e
contrato estatico/busy mock; nao e teste de scheduler remoto.

RISKS: governanca dev ainda nao aplicada; sem teste remoto novo; verificacao SHA nao
protege contra remocao do proprio guard; variaveis snapshot; atrasos/perda de ticks;
sem monitor independente configurado; humano ainda precisa aprovar SLA/cadencia/dono.
Sem commit/push, publicacao, variavel, secret, environment, sync, producao, SQL,
benchmark ou mudanca em fontes/demandas_inicie. Parar apos testes e relatorio.

Validacao YAML: blocos embutidos e contratos estaticos testados; nao foi executado
actionlint nem parser YAML completo (indisponiveis localmente). Nao se instalou
extensao/dependencia. Revisao de sintaxe GitHub completa integra o proximo gate.
