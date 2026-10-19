# Decisoes

## 2026-10-19 — redesenho da autorização Cron/Edge

Humano exige prova da origem Cron; wake público não pode consumir autorização.
Preparar SQL privado com capacidade Edge restrita e handler sem chave ampla;
ingresso autenticado real permanece bloqueador, sem aceitar mocks como prova.
[ADR do redesign](decisions/20261019_cron_edge_authorization_redesign.md).

## 2026-10-19 — probe sintético e leitura administrativa Supabase

Autorização humana restrita aceitou leitores internos privilegiados apenas
para estados sintéticos do probe. Prova real transacional GREEN, desativada,
sem deltas operacionais. Não aprova isolamento de secrets, Edge ou Cron.
Evidências e limites na [ADR](decisions/20261019_cron_single_controlled_dispatch_design.md).

## 2026-10-19 — revisão de preparação Cron staging

Manter integração Cron/pg_net/Edge bloqueada: ACL pg_net não é isolamento
suportado no Supabase hospedado, bearer reutilizável e service_role amplo
precisam correção. Preparar somente probe transacional isolado, sem extensões
ou HTTP, para aprovação humana. Detalhes e histórico na
[ADR](decisions/20261019_cron_single_controlled_dispatch_design.md).

## Formato

Data:
Decisão:
Motivo:
Alternativas consideradas:
Impacto esperado:

## 2026-08-19

Data: 2026-08-19
Decisão: quatro disposições operacionais e `sync_runs.id` cliente-gerado como identidade de execução.
Motivo: impedir retry cego de commit desconhecido e forçar releitura/diff em retries seguros.
Alternativas consideradas: classificação por mensagem e nova migration de idempotência.
Impacto esperado: retry limitado e reconciliação sem migration adicional.

## 2026-09-02

Data: 2026-09-02
Decisao: validar duas fontes independentes por `data_source_id` no mesmo projeto institucional.
Motivo: comprovar isolamento de identidade, schema, estado, lock e falha antes da camada analitica.
Alternativas consideradas: criar nova migration, paralelizar o lote ou criar segunda fonte no staging.
Impacto esperado: execucao sequencial multi-source com resumo agregado, sem DDL ou multi-tenancy.

## 2026-09-03

Data: 2026-09-03
Decisao: adotar para a entrega um Star Schema corrente e minimo de
categoria/pontuacao, conforme
`docs/decisions/20260903_minimum_analytical_contract.md`.
Motivo: demonstrar raw para analytics para BI com grain e metricas objetivos,
sem inventar dominio real nem promover payload ou PII desnecessaria.
Alternativas consideradas: Snowflake, history analitico, `DIM_DATE`, modelo
generico e uniao estrutural de fontes incompativeis.
Impacto esperado: proximo gate limitado a duas dimensoes e uma fato locais;
RBAC, dashboard e operacao produtiva permanecem gates posteriores.

## 2026-09-09

Data: 2026-09-09
Decisao: compor Google reader e core raw em um entrypoint staging dedicado, com
guard de destino, validacao fechada de source/lifecycle e reconciliacao efetiva
de commit ambiguo.
Motivo: permitir um gate remoto posterior sem reutilizar `apply-local`, duplicar
o pipeline ou aceitar configuracao persistida divergente.
Alternativas consideradas: script de demo independente e liberacao de host no
CLI local; ambas rejeitadas por contornarem contratos existentes.
Impacto esperado: dry-run sem writes e sync staging explicitamente confirmada,
mantendo production proibida. Detalhes em
`docs/decisions/20260909_staging_sync_composition.md`.

## 2026-09-11

Data: 2026-09-11
Decisao: propor Supabase Cron como scheduler global e uma Vercel Function
Python como worker serverless do MVP, condicionados a validação técnica.
Motivo: reutilizar o core Python, reduzir plataformas e manter o estado
operacional no Supabase sem executar ETL pesado no PostgreSQL.
Alternativas consideradas: Cloud Run, Railway/Render, GitHub Actions, Vercel
Cron, trigger Google em tempo real e worker permanente.
Impacto esperado: uma execução global diária no MVP, endpoint autenticado,
credenciais server-side e evolução para runtime dedicado quando limites
objetivos forem atingidos.

## 2026-09-30

Data: 2026-09-30
Decisao: preparar GitHub Actions como disparador manual de staging, reutilizando
o entrypoint Python oficial por source e sem agendamento recorrente.
Motivo: validar a borda de execução remota sem duplicar regras de sincronização
nem ativar Supabase Cron antes de existir um dispatcher central de fontes vencidas.
Alternativas consideradas: cron por cliente, workflow por cliente, Vercel e
seleção de agenda no YAML; rejeitadas neste gate.
Impacto esperado: um workflow seguro e serializado para o primeiro disparo
manual; o modelo de elegibilidade central permanece gate posterior. Detalhes em
`docs/decisions/20260930_github_actions_staging_dispatch.md`.
