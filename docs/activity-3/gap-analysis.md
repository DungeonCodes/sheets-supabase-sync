# Análise de lacunas da Atividade 3

Data da auditoria: 2026-08-06. Fonte: [documento oficial](../decisions/20260806_inicie_etl_clientes_orientacao.md). O inventário incluiu documentação, ADRs, migration ativa e históricas, seed, todo o pacote Python, scripts, testes, CI, configurações de exemplo e artefatos locais existentes. Nenhum segredo ou estado remoto foi consultado.

## Leitura dos resultados

“Implementado” significa que existe código ou DDL. “Validado” exige teste ou resultado registrado compatível com o alcance declarado. Preparação parcial, planejamento e hipótese não são tratados como entrega.

## 1. Atendido e validado

- Fundação remota: uma migration local/remota convergente; cinco tabelas operacionais; 27 constraints; 14 índices; RLS/grants coerentes; Data API acessível; zero policies, linhas ou tabelas espelho. Inspeção somente de leitura em 2026-08-06.
- Código Python modular, com dependência oficial Google mínima, domínio separado das bordas e SQL gerado de modo auditável (`DQ-04`, `PROC-05`).
- Schema drift offline: tipos, novas/ausentes, possível renomeação e incompatibilidade; mudanças bloqueantes preservam o snapshot (`PROC-01`).
- Isolamento de falha por fonte em batch, comprovado por teste comportamental (`PROC-02`).
- Barreiras contra segredo em artefatos, CI e erros; host remoto recusado no aplicador local (`SEC-02`).

O alcance é local/offline. Esses itens não comprovam Google, Supabase end-to-end, BI ou operação contínua.

## 2. Implementado, mas ainda não validado

- Leitor Google Sheets v4 somente leitura, autenticação oficial por Service Account, normalização mínima, erros tipados e retry seguro têm testes offline. A chamada real chegou à API, mas recebeu 403 antes dos metadados (`ING-03`).
- A estrutura, o runbook, o `doctor`, as fixtures e a CI preparam manutenção diária, mas não houve exercício por operador independente (`MAINT-01`).
- A documentação e a arquitetura favorecem continuidade por outro profissional, mas não houve handoff real (`MAINT-02`).

## 3. Parcialmente atendido

- Arquitetura ETL: núcleo offline existe; Google, transformação analítica e BI não (`OBJ-01/02`).
- Proteção: sanitização, isolamento e RLS fechado existem; LGPD, anonimização e acesso por usuário não (`OBJ-03`, `DQ-03`).
- Desempenho: há teste opt-in de 10.000 linhas, mas sem teto de duração e sem banco/dashboard (`DQ-01`).
- Custo zero: stack atual é enxuta, porém planos gratuitos e custo futuro não foram estudados (`DQ-02`).
- Quotas/rate limit: limites oficiais, 429, backoff+jitter, `Retry-After`, orçamento e telemetria local foram implementados; faltam cota efetiva, rate limiter global e carga multi-fonte (`ING-01`).
- Frequência: configuração e seleção de fontes vencidas existem; a cadência e o scheduler operacional não (`ING-02`).
- Observabilidade: eventos seguros, health e tabelas existem; centralização, retenção e alertas reais não (`PROC-03`).
- Raw: DDL, payload JSON e snapshots existem; o fluxo Python não persiste `raw_import_rows` (`STORE-02`).
- RLS/RBAC: RLS bloqueia acesso frontend às tabelas operacionais, mas não há hierarquia ou policies por escopo (`STORE-04`).
- Último dado válido: snapshots não avançam em drift bloqueante, mas não há camada servida/BI nem recuperação testada (`AVAIL-01`).
- Credenciais: arquivos locais ignorados e sanitização existem; falta cofre, rotação e ownership (`SEC-01`).

## 4. Não implementado

- Resolver a autorização 403 e comprovar metadados, aba, cabeçalho e linhas da fixture privada.
- Rate limiter global e telemetria centralizada de quotas.
- Scheduler implantado e quase tempo real/eventos.
- Persistência raw ponta a ponta e camada staging.
- Modelo analítico, Star Schema/Snowflake, fatos, dimensões e transformações SQL analíticas.
- Ferramenta de BI, dashboard, tempos de carregamento e filtros de usuário.
- Alertas por e-mail, deduplicação e mensagem de recuperação.
- Política de retenção de logs/raw, anonimização e procedimento LGPD.
- Estudo dos planos gratuitos, custos futuros e proteção pay-as-you-go.
- Onboarding, backfill/migração histórica e reconciliação do cliente.
- Planos B e C por ferramenta.
- Fluxograma Draw.io e exportação.
- Backup externo e teste de restauração.

## 5. Bloqueado por decisão externa

- Frequência e necessidade de quase tempo real.
- Volumes médio/máximo, SLA de atualização e desempenho.
- Ferramenta de BI, usuários e escopos de acesso.
- Retenção, anonimização, orçamento e tolerância a custo.
- Responsáveis por onboarding e credenciais, canal de alerta, RTO e backup externo.

As perguntas estão em [open-decisions.md](open-decisions.md); nenhuma resposta empresarial foi presumida.

## 6. Dependente de pesquisa

- Limites atuais e termos dos free tiers de Supabase, BI, alertas e scheduler; a Sheets API foi pesquisada em 2026-08-06.
- Opções de Data Warehouse/banco analítico e BI compatíveis com custo, RLS e volume.
- Cenários de custo e risco pay-as-you-go.
- Alternativas B/C e esforço de portabilidade/lock-in.
- Requisitos legais e organizacionais concretos de retenção, minimização e anonimização.

Toda pesquisa temporal deverá ser datada e citar documentação oficial; suposição não será evidência.

## 7. Dependente de acesso ou dados do cliente

- Service Account de homologação e planilha fictícia compartilhada com mínimo privilégio.
- Projeto Supabase de staging autorizado para gates que exigem ambiente real.
- Perfis fictícios representativos dos escopos de usuário.
- Amostras sintéticas representativas de volume e schema; dados reais não são necessários para o MVP.
- Aceite do processo de onboarding, reconciliação e dashboard.

## Avaliações explícitas

| Capacidade | Estado real | Classificação |
| --- | --- | --- |
| Google Sheets API real | GET real executado com token em memória e escopo read-only; API respondeu 403 antes de retornar metadados. | implementado; autorização remota bloqueada |
| Quotas e rate limit | Quotas oficiais documentadas; retry integrado com jitter, orçamento e `Retry-After`; sem coordenação global. | parcial |
| Batch versus quase tempo real | Intervalo configurável e seleção de vencidas; decisão/SLA e scheduler ausentes. | parcial / decisão externa |
| Backoff exponencial | Integrado ao leitor para 429/5xx/timeout/rede, com jitter, `Retry-After` e testes offline. | implementado, validação real pendente |
| Isolamento por fonte | Batch captura falha de uma fonte e continua; teste aprovado. | validado offline |
| Schema drift | Tipos, colunas, possível rename e bloqueio cobertos. | validado offline; integração pendente |
| Dados brutos | Estrutura SQL, payload JSON e snapshot; sem persistência integrada. | parcial |
| Staging | Nenhuma camada específica. | não implementado |
| Star Schema / fato / dimensão | Nenhum objeto ou transformação analítica. | não implementado |
| Ferramenta de BI | Nenhuma escolha ou conexão. | bloqueado por decisão |
| RLS por usuário | RLS fechado nas tabelas operacionais; sem policies/hierarquia. | parcial |
| Alertas por e-mail | Regras de severidade existem; entrega não. | não implementado |
| Último dado válido | Snapshot é preservado em drift bloqueante; serving/BI não existe. | parcial |
| Retenção de logs e raw | Não definida. | decisão/pesquisa |
| Anonimização e LGPD | Apenas guardrails de segredo e aviso sobre PII raw. | parcial insuficiente |
| Plano gratuito e custos futuros | Sem pesquisa citada ou modelo. | não implementado |
| Onboarding e migração histórica | Sem procedimento ou teste. | bloqueado por decisão/dados |
| Planos B e C | Sem matriz. | não implementado |
| Draw.io | Sem `.drawio` ou exportação. | não implementado |
| Manutenção por outro profissional | Base legível e documentada; handoff não executado. | implementado, não validado |

## Próximo marco e ordem segura

O próximo marco técnico é **MVP ponta a ponta com dados fictícios**:

```text
Google Sheets fictício → Python → Supabase Raw → transformação SQL simples
→ tabela analítica → consulta pronta para BI
```

A fundação do staging permanece validada e nenhuma escrita ocorreu neste gate. O próximo passo único é **revisar externamente a autorização da Sheets API/fixture e repetir o diagnóstico read-only**. A Fase 2 não pode começar antes da leitura fictícia bem-sucedida.
