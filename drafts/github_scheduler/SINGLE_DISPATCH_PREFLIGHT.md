# GITHUB_CLOCK_SINGLE_MANUAL_DISPATCH_PREFLIGHT

20/10/2026. **GREEN para preflight; teste real NÃO executado nem autorizado.**
Só documentação modificada. Nenhuma repository variable, secret, workflow,
environment, código Python ou objeto PostgreSQL alterado.

## Estado observado e reconfirmado

- Host DESKTOP-VU6VMS6; raiz sheets-supabase-sync; branch local dev, inicialmente
  limpa, HEAD `c6d13b686eb060bc4c3c6defdd5663c57861d4f4`, igual à dev remota.
- Default branch main, SHA remoto atual `80cdde4bb79506deecb3d37f0e9894fba03739ac`.
- Clock ativo/acessível, ID 390540622, path .github/workflows/staging-clock.yml.
  Blob `2e4f176567d6b5a038dcc0d00f9b6f938475d7ee`, idêntico ao draft manual testado.
  Somente workflow_dispatch; nenhum schedule, environment ou secrets de dados.
- Zero runs de clock, nenhuma ativa. **Próximo run_number esperado: 1**. Valor
  derivado do inventário atual, não reserva de número; repetir antes de armar.
- STAGING_CLOCK_ENABLED: **UNSET**, sem valor existente; efeito fail-closed.
- STAGING_CLOCK_AUTHORIZED_RUN_NUMBER: **UNSET**, sem valor existente. Nenhuma
  repository variable configurada; valores conferidos por GET, nada alterado.
- Executor scheduled-sync.yml ativo, ID 388468858, blob dev
  `65d16e28a9e00918a0eac2213ab57b0e73fc6ea0`, preservado. Sua única run anterior
  é 39247320871, run_number 1, completed/success, dev. Nenhuma run ativa; próxima
  numeração do executor pode ser 2, mas identidade será o run_id retornado.
- Só três workflows registrados: CI, executor e clock; nenhum relógio adicional.
- Environment staging: única política branch **dev**, sem tags; proteção é por
  branch, não por identidade de workflow. Sete secrets confirmadas só por nomes:
  APP_ENV, GOOGLE_SERVICE_ACCOUNT_JSON, STAGING_SYNC_CONFIG_JSON,
  SUPABASE_ALLOWED_PROJECT_REF, SUPABASE_DB_URL, SUPABASE_PROJECT_REF, SUPABASE_URL.
  Não lidos os valores nem comprovada igualdade entre secret config e config local.
- Actions enabled, allowed_actions all, default_workflow_permissions **read**;
  clock declara topo permissions vazio e job actions:write + contents:read.
  Override explícito é documentado e adequado ao dispatch no mesmo repo e GET da
  revisão dev. CLI local/mocks não comprovam token efetivamente emitido; observar
  permissões do job no teste autorizado. 401/403 interrompem, sem fallback PAT.

## Leitura staging e dry-selection efetivamente executados

Usados `load_environment`, `validate_staging_access`, config local autorizada
runtime/forms_demo.config.json e entrypoint `batch_cli.run_cli --dry-select`.
Nenhuma implementação ou arquivo Python criado/modificado. Operation do apply
substituída em memória por bloqueio, de modo que seleção não pode executar sync.
Saída filtrada em memória para contadores/status, sem nomes/IDs de planilha.
O carregador operacional existente usa SET TRANSACTION READ ONLY e rollback;
conexões adicionais explicitamente read_only, com default_transaction_read_only=on,
connect_timeout 10s, statement_timeout 10s e lock_timeout 2s. Guard staging PASS,
project_ref igual à allowlist, TLS cliente ativo, transaction_read_only=on.

Baseline antes: **2026-10-20T13:29:04.713099Z**. Depois:
**2026-10-20T13:29:07.468940Z**.

| Métrica | Antes | Depois | Delta |
|---|---:|---:|---:|
| sync_runs global | 9 | 9 | 0 |
| raw_import_rows global | 11 | 11 | 0 |
| raw_current_rows global | 8 | 8 | 0 |
| planned/running global | 0 | 0 | 0 |
| fontes do escopo configurado | 1 | 1 | 0 |
| sync_runs do escopo | 3 | 3 | 0 |
| eventos raw do escopo | 3 | 3 | 0 |
| estados atuais do escopo | 3 | 3 | 0 |

Último sucesso da fonte: 2026-10-19T11:48:49.361510Z. Fingerprint agregado de
row_key_hash/content_hash/version/is_deleted do escopo:
`2955c6490ddec36688043aafc3e36cb5`, idêntico antes/depois. Não inclui payloads,
não é assinatura criptográfica de autenticação nem mede todas as tabelas.

Dry-selection exit 0, selected/dry_select/staging: total=1, due=1,
executed=0, no_changes=0, skipped=0, failed=0, busy_deferred=0. Uma fonte due;
nenhuma chamada Google, run nova ou persistência. Isso não confirma conteúdo atual
da planilha nem resultado futuro no_changes. Baseline envelhece; atualizar antes
do teste aprovado e parar se houver divergência não explicada.

## Inputs validados e procedimento FUTURO — não executar sem aprovação

Origem main; alvo fixo dev e scheduled-sync.yml no repositório atual. Inputs:
confirm_dispatch **true**, expected_dev_sha **c6d13b686eb060bc4c3c6defdd5663c57861d4f4**
(usar só se ainda atual e congelado), approval_expires_at UTC ISO Z no máximo
15 minutos à frente no instante em que o clock verifica. Não fornecer expiração
fixa neste relatório: gerar imediatamente após autorização, por exemplo +10 min.
Fila/atraso que expire janela encerra autorização; não repetir automaticamente.

1. Obter **APROVAR UM DISPARO MANUAL DO RELÓGIO**, incluindo explicitamente armar
   temporariamente as duas variables e desarmar ao final. Autorização ainda não
   concedida neste gate. Não inferir da publicação ou deste GREEN.
2. Revalidar SHAs/main/dev/workflow blobs, políticas staging e sete nomes de
   secrets; confirmar nenhum clock novo e nenhuma run ativa de clock/executor,
   nem planned/running em staging. Repetir baseline e due-selection read-only.
   Congelar dev e alterações concorrentes até conclusão. Se algo mudar, parar
   e revisar autorização; não usar automaticamente valores deste relatório.
3. Somente sob aprovação, confirmar número esperado ainda 1, configurar
   STAGING_CLOCK_AUTHORIZED_RUN_NUMBER=1 e STAGING_CLOCK_ENABLED=true. Conferir
   GET dos dois valores; não alterar defaults de permissão ou secrets.
4. Gerar expiração UTC e chamar **uma vez** o clock main, nunca o executor direto.
   Comandos abaixo são procedimento futuro, não foram executados:

```powershell
gh variable set STAGING_CLOCK_AUTHORIZED_RUN_NUMBER --repo DungeonCodes/sheets-supabase-sync --body '1'
gh variable set STAGING_CLOCK_ENABLED --repo DungeonCodes/sheets-supabase-sync --body 'true'
$clockExpiry = [DateTime]::UtcNow.AddMinutes(10).ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
gh workflow run staging-clock.yml --repo DungeonCodes/sheets-supabase-sync --ref main -f confirm_dispatch=true -f expected_dev_sha=c6d13b686eb060bc4c3c6defdd5663c57861d4f4 -f approval_expires_at=$clockExpiry
```

5. Observar por GET a nova run do workflow 390540622: run_number=1, attempt=1,
   main/SHA aprovado/event workflow_dispatch. Capturar clock_run_id real; não
   confundir ID do workflow, número sequencial e run_id. Consultar logs só em
   memória e extrair allowlist de registros JSON: tentativa pré-POST, SHA/horários,
   status HTTP e executor_run_id validado. Não persistir logs/corpos brutos/tokens.
6. Resposta do clock `dispatch_accepted_not_completed` não comprova sync. Consultar
   exatamente o filho retornado: workflow 388468858, dev/SHA/attempt=1, jobs e
   deployment staging/guard/cleanup. Acompanhar até terminal. Não confiar só no
   verde do GitHub ou exit code 0: capturar resumo do step de dispatch e verificar
   sources_total/due/executed/no_changes/skipped/failed/busy_deferred.
   sources_failed>0 = SOURCES_FAILED; busy>0 = deferido, sem retry de workflow.
   Ausência de resumo/identidade/guard = UNKNOWN/bloqueado. Usar helper offline
   executor-observation.mjs como apoio, conferindo proveniência do resumo.
7. Ao clock terminar ou a tentativa tornar-se ambígua, **desativar opt-in**, sem
   cancelar sync/commit em andamento. A alteração de variável não cancela um job
   já iniciado. Manter observação do filho e reconciliar antes de fechar o gate.

```powershell
gh variable set STAGING_CLOCK_ENABLED --repo DungeonCodes/sheets-supabase-sync --body 'false'
gh variable delete STAGING_CLOCK_AUTHORIZED_RUN_NUMBER --repo DungeonCodes/sheets-supabase-sync
```

8. Reconciliação READ ONLY: baseline global/escopo, runs novas, seus estados e
   contadores, eventos/estado e fingerprint. Uma sync no_changes esperaria +1 run,
   zero eventos/estado alterados; isso é expectativa condicional, não promessa.
   Vincular janela/source e ausência de concorrência; GitHub run_id não é UUID
   sync_runs e não há vínculo persistido direto. Se dados mudarem, reconciliar
   com contadores reais; não impor 9/11/8 como resultado final invariável.
   Confirmar opt-in false/authorization ausente e ausência de runs inesperadas.

## Interrupção e ambiguidade

Parar imediatamente em ref/blob diferente, nova run de clock, número consumido,
concorrência, environment/regra/secrets inconsistentes, falha de guard/config,
erro de autenticação/API, expiração, busy, sources_failed, resumo inválido ou
baseline divergente sem causa. Não aumentar permissões globais ou criar PAT.

Timeout no primeiro comando manual também pode ter criado a run do clock: ler
GitHub antes de qualquer ação. Timeout no POST interno pode ter criado filho:
desarmar e consultar clock e candidatos do executor por janela/ref/SHA/ator.
Se houver ID conhecido, observar somente ele. Sem correlação inequívoca, manter
UNKNOWN; não rearmar, reenviar, dar rerun, avançar número ou chamar executor
direto. Uma autorização consumida por erro/skip requer nova decisão humana.
Concurrency reduz sobreposição, não exactly-once; locks/elegibilidade Python
permanecem necessários. Não há garantia contra outros atores/acionadores externos.

## Fontes oficiais verificadas

- [Permissions por job](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions).
- [REST dispatch e Actions:write](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).

## Resultado

```text
STATUS: GREEN (preflight somente; ainda sem autorização de teste)
CLOCK_WORKFLOW: staging-clock.yml ACTIVE, ID 390540622, somente workflow_dispatch
MAIN_SHA: 80cdde4bb79506deecb3d37f0e9894fba03739ac
DEV_SHA: c6d13b686eb060bc4c3c6defdd5663c57861d4f4
CLOCK_RUN_NUMBER: 1 EXPECTED; zero execuções anteriores
CLOCK_ENABLED: UNSET (bloqueado)
AUTHORIZED_RUN_NUMBER: UNSET
EXECUTOR_STATE: ACTIVE/IDLE; execução anterior GREEN preservada
SOURCES_DUE: 1; sources_executed=0; sources_failed=0
STAGING_BASELINE: 9/11/8 global; 0 planned/running; deltas zero após dry-selection
RISKS: baseline e SHAs móveis, segredo remoto não inspecionável, token emitido não comprovado, ambiguidade/concorrência
NEXT_APPROVAL: APROVAR UM DISPARO MANUAL DO RELÓGIO
```

Nenhuma variável alterada, clock/executor executado, schedule habilitado, código,
secret, produção, migration ou Git de escrita acessado. Aguardar aprovação humana.
