# GITHUB_CLOCK_RECURRENCE_READINESS_REVIEW — 2026-10-21

STATUS: YELLOW
ARCHITECTURE: GITHUB_ACTIONS_CLOCK
MANUAL_MODE_PRESERVED: YES
SCHEDULED_MODE_READY: NO (candidato offline testado; pendencias abaixo)
SCHEDULE_ENABLED: NO
OPT_IN_DEFAULT: DISABLED
SOURCE_FREQUENCY_INDEPENDENT: YES
NEXT_GATE: GITHUB_CLOCK_SCHEDULE_PUBLICATION_PREPARATION

## Escopo e preflight

Leituras somente; nenhum teste remoto repetido. Worktree inicialmente limpo.
Repositorio publico DungeonCodes/sheets-supabase-sync; hostname DESKTOP-JJA98HA;
branch local dev; HEAD 14b6672908fddf688905d8a96d66e78d78b9851d.
origin/main e main remoto: 80cdde4bb79506deecb3d37f0e9894fba03739ac.
origin/dev e dev remoto: 294dceb07ad131a0b45f84b79b611b126e0e9558.
Branch padrao main. Ambas branches retornaram protected=false; rulesets nao
foram auditados, portanto nao se presume revisao obrigatoria efetiva.
Checkout local nao contem staging-clock.yml; baseline veio de contents API main.
Workflows registrados ativos: ci.yml, scheduled-sync.yml e staging-clock.yml.
Active indica workflow habilitado, nao recorrencia: baseline somente workflow_dispatch.
Repository variables: lista vazia (inclusive temporarias e novo opt-in ausentes).
Environment staging: politica customizada, unica branch permitida dev.
Secrets do repositorio: nenhum retornado. Secrets staging, somente nomes:
APP_ENV, GOOGLE_SERVICE_ACCOUNT_JSON, STAGING_SYNC_CONFIG_JSON,
SUPABASE_ALLOWED_PROJECT_REF, SUPABASE_DB_URL, SUPABASE_PROJECT_REF, SUPABASE_URL.
Nenhum valor de secret ou dado de fonte foi lido ou persistido.

Metadados dos runs ja concluidos, sem rerun: clock 39478296467, success,
18:50:47–18:50:57 UTC em 2026-10-20 (10 s); executor 39478314244, success,
18:50:54–18:51:15 UTC (21 s). Estas sao janelas de run, nao medicao de CPU,
P95 ou capacidade. Uma amostra nao permite definir cadencia nem escala.

## Arquitetura e revisao

main -> clock -> workflow_dispatch fixed scheduled-sync.yml/ref dev -> dispatcher
Python existente -> staging. Clock sem checkout, actions terceiras, environment,
Google/Supabase secrets, PAT ou retry. GITHUB_TOKEN actions:write/contents:read;
permissions globais vazias. Somente repositorio, workflow e main fixos sao aceitos.

Manual preserva opt-in STAGING_CLOCK_ENABLED=true, numero autorizado, confirmacao,
SHA esperado, janela UTC <=15 min, tentativa 1 e identidade pos-dispatch.
Scheduled usa exclusivamente STAGING_CLOCK_SCHEDULE_ENABLED=true (literal exato)
e STAGING_CLOCK_APPROVED_DEV_SHA valido/coincidente com dev; numero manual nunca
autoriza schedule. Ausente, vazio, false ou valor desconhecido bloqueia antes de API.
Nenhum cron foi escolhido ou inserido; evento scheduled e exercitado por mocks.
O candidato nao e publicavel como recorrente sem gate posterior.

| Politica | Manutencao | Seguranca |
| --- | --- | --- |
| Qualquer SHA valido de dev | nenhuma atualizacao de autorizacao | toda mudanca de dev torna-se executavel; depende totalmente da governanca da branch |
| SHA aprovado | atualizar somente ao promover nova revisao | trilha explicita; dev divergente bloqueia, risco de indisponibilidade por esquecimento |
| Revisao atualizada sob processo controlado | revisao/CI e registro por promocao, nunca por tick | recomendacao provisoria: SHA aprovado mais protecao/revisao de dev; nao ha automacao de aprovacao neste gate |

Variavel proposta STAGING_CLOCK_APPROVED_DEV_SHA e independente do opt-in e nao
foi criada. Preferir promocao revisada; humano aprova a politica final.
Dev e consultada duas vezes antes de POST; run retornado deve corresponder ao SHA.
API dispatch por branch nao oferece comparacao atomica com SHA: corrida entre GET
e POST pode iniciar revisao distinta antes de ser detectada. Congelar/promover dev
sob processo controlado reduz janela; verificacao preventiva dentro do executor
seria outro escopo e exige revisao, nao implementada. Nao afirmar pin atomico.

## Frequencia e custo

Nenhum SLA, inventario de intervalos ou quantidade futura de clientes confirmado;
nao acessar configuracao secreta para descobri-los. Dispatcher permanece dono de
sync_interval_minutes, lifecycle, enabled e ultima aplicacao valida. Tick nao obriga
sync. NO_CHANGES e sem fontes elegiveis sao estados diferentes.

| Opcao para discussao | Ticks/dia | Ticks/30 dias | Quando considerar |
| --- | ---: | ---: | --- |
| 5 min | 288 | 8640 | somente SLA curto comprovado; maior overhead e frequencia minima GitHub |
| 15 min | 96 | 2880 | fontes frequentes e tolerancia compativel |
| 30 min | 48 | 1440 | atualizacao moderada |
| 60 min | 24 | 720 | fontes horarias ou menos frequentes |

Nenhuma selecionada. Evitar inicio da hora; offsets/cron/timezone dependem de aprovacao.
Atraso adicional ideal apos fonte vencer e ate intervalo do clock, mais fila,
atraso GitHub e duracao; nao constitui limite garantido. Execucao maior que intervalo
pode acumular/substituir pendencias e reduzir throughput. SLA estrito pede reavaliacao.
Estimativa ilustrativa com amostra 10+21 s por tick: 4464/1488/744/372 runner-min
respectivamente por 30 dias, sem arredondamento; nao e previsao de faturamento.
Standard hosted runners em repo publico: custo de computacao GitHub estimado US$0.
Storage/artifacts, mudanca para privado/larger runners e servicos externos separados.
Google: leituras reais dependem de fontes devidas, linhas e requests por fonte;
PostgreSQL: selecao a cada tick, locks e escrita somente conforme processamento.
Modelo: ticks * custo de selecao + execucoes elegiveis * custo por source; dimensionar
por clientes/fontes/volume e duracao observada sem benchmark neste gate. Pendentes
SLA por fonte, intervalos, volume, concorrencia tolerada e orcamentos Google/DB.

## Concorrencia, duplicidade e reconciliacao

DUPLICATE_PROTECTION: grupo staging-clock comum a manual/scheduled, cancel false;
consulta paginada (limite 10 paginas; inconclusivo bloqueia) das execucoes de dev;
executor conserva staging-dispatch-${github.ref}, locks por source e elegibilidade.
Teste de busy e simulacao da API, nao simulacao do scheduler do GitHub.
Ticks proximos/manual simultaneo serializam clock, mas clock termina apos aceite.
Executor ativo causa busy_skip. Executor direto pode correr entre verificacao e POST;
concurrency do executor e locks sao defesa final, nao garantia de unicidade.
Por padrao grupo admite um running e um pending; novo pending substitui o anterior;
nao se presume FIFO nem se habilita novo modo de fila neste candidato.
Falha GET bloqueia; POST uma unica tentativa; transporte/5xx/resposta invalida ou SHA
diferente depois do POST = ambiguo, pode ter executado. Nunca redespachar automaticamente.
Correlacionar clock_run_id -> executor_run_id retornado pela API; validar workflow,
evento, branch, attempt e SHA. Sem run_id confiavel, reconciliar manualmente janela,
workflow, SHA e sync_runs; nao inferir sucesso por HTTP ou marcar exactly-once.
Sem backfill de ticks perdidos: proximo tick reavalia due; nao garante SLA.

## Observabilidade e alertas

Modelo publico sanitizado, sem source IDs/clientes/linhas/URLs privadas:
mode, expected_at, actual_at, clock_run_id, executor_run_id, clock_sha, executor_sha,
sources_due, sources_executed, sources_failed, sources_busy_deferred, final_state,
duration_seconds, last_success_at. Nulos significam desconhecido, nunca zero implicito.
Clock candidato registra mode/at/run IDs/SHA/estado de aceite. expected_at=null ate
aprovar cadencia; created_at do run nao prova horario nominal. Nao registra metricas
finais do executor nem ultima sync: aceite nao e conclusao.
Executor ja emite resumo agregado; observador futuro deve unir IDs e resumo sanitizado,
conclusion, started/completed. last_success_at: ultima conclusao saudavel com resumo
valido e sources_failed=0; registrar separadamente ultima aplicacao por fonte (DB).
No eligible: saudavel para tick, nao prova frescor das fontes. Busy exige reconciliacao.
Staging indisponivel: falha/exit 2 ou resumo ausente -> alertar, sem retry.

observation.mjs e especificacao executavel offline; NAO esta conectado ao executor.
MISSED_TICK_DETECTION: slots esperados da cadencia aprovada vs runs observados,
tolerancia humana pendente; atrasado, ausente e workflow desabilitado sao distintos.
Proximo tick consegue notar lacuna anterior, mas nao detecta silencio permanente.
Sem infraestrutura extra: operador responsavel revisa Actions/estado/variavel e ultima
execucao em rotina com prazo aprovado. Para deteccao automatica durante silencio,
precisa monitor independente; nao prometer cobertura com o proprio clock parado.
Schedule off intencional registra manutencao, nao falha operacional por si so.

FAILURE_ALERTING: usar notificacoes nativas Actions para falhas reais e responsavel
inscrito; validar recebimento no gate futuro. Sources_failed>0 com exit 0 NAO gera
notificacao nativa de failure hoje. Antes da ativacao, adaptar em draft o consumidor
sanitizado do resumo para falhar o job/observador em partial failure e falha de parsing.
Nao publicar logs brutos: repo publico e resumo atual inclui identidades de sources.
Decidir se mascarar/reduzir esses logs antes de recorrencia. Contador de falhas
consecutivas deve usar runs reconciliados, nao aceite do clock; limiar e destinatario
pendentes. Sem Slack/email/issue automaticos criados neste gate.

## GitHub: documentacao oficial consultada em 2026-10-21

- [Schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule): branch padrao/ultimo commit; cron POSIX, minimo 5 min, UTC default e timezone IANA opcional, efeitos DST; atraso/descarte em alta carga; repo publico desabilita apos 60 dias inativo. Nao ha pontualidade garantida.
- [Concorrencia](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency): default substitui pending; queuing explicito existe, nao adotado.
- [Token](https://docs.github.com/en/actions/concepts/security/github_token): restrito ao repo, dispatch e excecao que cria outro run sem PAT.
- [REST dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event): Actions write, ref obrigatoria; API 2026-03-10 retorna HTTP 200 com ID/URLs. Candidato mantem contrato ja validado, nunca presume antigo 204 como sucesso correlacionado.
- [Limites](https://docs.github.com/en/enterprise-cloud@latest/actions/reference/limits): hosted job ate 6h, Free standard concurrency 20 (plano efetivo nao auditado), GITHUB_TOKEN 1000 requests/h/repo; limites secundarios tambem se aplicam. Timeout proprio clock 3min/executor 20min.
- [Custos](https://docs.github.com/en/billing/concepts/product-billing/github-actions): standard runners publicos gratuitos; larger runners cobrados; storage tem limites/custos proprios.
- [Troubleshooting](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows): ator suspenso/removido pode parar schedule; reativacao e acao controlada, nao alterar cron automaticamente.

## Ativacao futura e rollback — NAO executar neste gate

1. Aprovar cadencia/timezone/tolerancia, politica de revisao, responsavel e limites.
2. Resolver partial-failure alert, privacidade de logs e rotina de silencio; revisar
   diferencas main/dev e preparar publicacao no proximo gate. Main nao contem este draft.
3. Publicar candidato revisado e cron somente em gate autorizado, com opt-in ausente.
   Verificar bloqueio e versionamento por testes; sem dispatch real neste gate.
4. Na Settings > Secrets and variables > Actions > Variables, apos aprovacao humana,
   configurar STAGING_CLOCK_APPROVED_DEV_SHA com revisao promovida e depois
   STAGING_CLOCK_SCHEDULE_ENABLED=true. Registrar aprovador, UTC, SHA clock/executor,
   cadencia, justificativa e rollback em docs/run_log.md/decisions. Nenhum PAT novo.
5. Confirmar estado por leitura da variavel, workflow active, default main, revisao e
   historico. Workflow conter schedule nunca e autorizacao suficiente.
6. Para desativar: remover opt-in ou definir false; registrar horario e motivo.
   Variaveis do contexto sao snapshot: mudanca nao revoga job ja iniciado/enfileirado.
   Em urgencia, desabilitar workflow clock e revisar/cancelar clock pendente antes do
   POST; nao presumir cancelamento de executor transacional seguro.
7. Reconciliar executores aceitos/em curso antes de declarar parado. Nao cancelar
   transacao por rotina; locks e resultado do executor precisam de acompanhamento.
8. Rollback estrutural: opt-in off primeiro, restaurar manual-baseline.yml via revisao
   humana futura, manter executor/secrets/environment. Nao reverter dados, migrar SQL
   nem reexecutar automaticamente. Reativacao exige novo registro de opt-in.

## Validacao e limites

node --test drafts/github-clock-recurrence/clock.test.mjs
35 testes aprovados, 0 falhas. Executam o programa embutido exato com fetch mockado;
nenhuma chamada GitHub/Supabase/Google durante testes. Cobrem manual/scheduled,
opt-in ausente/desativado, autorizacoes, concorrencia busy/grupo comum, SHA invalido
ou divergente, API indisponivel/503, resposta ambigua/corrida sem retry, secrets fora
do workflow e token fora dos logs, partial failure, no eligible, staging indisponivel,
tick perdido/atrasado e workflow desabilitado. Monitor testado e somente modelo.
Nao houve instalacao de dependencias, SQL, benchmark, dispatch, variavel ou secret
alterado, commit/push ou mudanca em .github/workflows. demandas_inicie intocado.
Python local via comando python indisponivel (uv trampoline); nenhum codigo Python
foi modificado, testes usam Node nativo v24.14.0 sem dependencias novas.

HUMAN_DECISIONS_REQUIRED: frequencia/SLA/timezone; politica de revisao e protecao
de dev; tratamento da corrida branch/SHA; alerta parcial, privacidade dos logs e
responsavel por silencio; limiar de falhas consecutivas e orcamentos. Gate encerrado
apos testes offline, sem reabrir gates GREEN e sem autorizacao de ativacao.
