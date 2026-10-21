# SCHEDULER_ARCHITECTURE_DECISION

**Status: PROPOSTA — PENDENTE DE APROVAÇÃO HUMANA.** Data: 19/10/2026.
Recomendar B para um teste controlado futuro; não ativar, não escolher frequência
definitiva e não abandonar oficialmente Supabase Cron nesta decisão proposta.

## Problema e alternativas

A: Supabase Cron → pg_net → Edge autenticada → GitHub → Python. A autenticação
do emissor permanece não resolvida sem credenciais adicionais/fronteira segura.
O probe PostgreSQL GREEN não valida essa autenticação. Nenhuma infraestrutura
operacional da arquitetura A foi implantada; rascunhos/evidências serão preservados.

B: relógio separado na main → GITHUB_TOKEN do job com Actions:write →
workflow_dispatch ref dev → workflow existente/environment staging → dispatcher.
Não mover secrets nem Python para main. Não é necessário PAT ou endpoint Edge.

## Evidências e recomendação

Repositório público, branch padrão main, Actions habilitado, destino ativo e
mesmo scheduled-sync.yml em main/dev/local. Environment staging mantém uma única
política branch dev e sete secrets conferidas apenas por nome. Default de token
read; job do relógio declara actions:write e contents:read, sem mudar defaults
ou permissões do destino. Dispatch interno com GITHUB_TOKEN é suportado pela
API e pela exceção documentada a novos eventos. Token efetivamente emitido e
novo handoff ainda precisam de teste real separado; a CLI local não o comprova.

Recomendar B por reduzir componentes, superfície e gestão de credenciais,
reutilizando a execução Python já validada. Runner padrão de repo público tem
execução gratuita documentada, sem promessa de custo total zero. Permanecem
limites de schedule/quotas/inatividade e necessidade de observação/reconciliação.

## Preparação e limites

[Pacote revisável, matriz e planos](../../drafts/github_scheduler/README.md),
YAML somente drafts/, sem schedule ativo. Opt-in ausente bloqueia; manual de
teste exige confirmação/SHA/expiry, recusa rerun e tenta um POST sem retries.
Relógio sem checkout/actions terceiras/environment/secrets de dados.
Mantém job alvo e seus grupos existentes; não altera SQL/Python.

Schedule não assegura horário exato; pode atrasar/perder ticks e ser desativado
por inatividade de repo público. Fila padrão do destino pode substituir run
pendente; preflight de concorrência é sujeito a corrida. Não existe deduplicação
durável/exactly-once. Se dev avançar entre a leitura e o dispatch, a verificação
posterior detecta, mas não impede Python: congelar dev no teste ou revisar guard
adicional futuramente. Não passar inputs que o destino ainda não declara.

## Aprovações e rollback

Primeiro aprovar esta ADR. Depois, em gate distinto, revisar publicação inativa
e autorizar um teste manual do relógio que pode provocar uma sync real em staging.
Conferir token do job, parent/child IDs, environment, guard/Python/dispatcher e
reconciliar baseline. Nenhum novo teste foi executado neste gate.

Só escolher/ativar frequência após confirmar requisitos dos clientes: tolerância
a atraso/perda, timezone, volume, backlog e monitoramento. A aprovação de B não
autoriza apagar A; decidir sua continuidade/arquivamento em aprovação explícita.
Rollback futuro desabilita apenas relógio/opt-in, preserva worker manual/secrets,
acompanha runs já aceitos e não repete dispatch ambíguo. Nada requer rollback
operacional agora porque nenhum recurso foi ativado por este gate.

Fontes e detalhes de testes no pacote. Próxima aprovação:
**APROVAR ADR PROPOSTA DE RELÓGIO GITHUB ACTIONS**.
