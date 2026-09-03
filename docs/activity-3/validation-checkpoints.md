# Checkpoints de validação da Atividade 3

## Estado atual do checkpoint

Os gates integrados de carga inicial, idempotência, update, tombstone, restore e reorder de linhas foram validados no staging exclusivamente com a fixture fictícia. Migrations permanecem 3/3. No gate de schema drift, coluna adicionada/removida e rename foram bloqueados antes de persistência; reorder de headers foi compatível por mapeamento por nome e header duplicado foi rejeitado antes da transação. As seções cronológicas abaixo preservam checkpoints históricos e não anulam este estado atual.

## Regra obrigatória

**Nenhuma fase é considerada concluída apenas porque o código foi escrito.**

Uma fase só é concluída quando:

- requisito rastreado;
- implementação existente;
- testes aprovados;
- resultado validado;
- riscos atualizados;
- documentação atualizada;
- critério de aceite comprovado;
- pendências registradas.

Além disso, SQL aplicável, segurança, custos, LGPD, ferramenta e passagem de fase exigem validação humana. Evidência deve indicar data, ambiente e alcance sem expor segredo ou dado real.

## Os nove gates obrigatórios

| Gate | Pergunta de controle | Evidência mínima | Condição de bloqueio |
| --- | --- | --- | --- |
| 1. Requisitos | IDs, alcance e aceite estão rastreados? | Matriz atualizada e vínculos para entregáveis | Requisito sem ID, ambíguo ou marcado validado sem prova |
| 2. Arquitetura | A mudança corresponde à arquitetura/ADR e mantém limites claros? | Diagrama/documento, ADR quando durável e revisão de dependências | Divergência não decidida ou acoplamento inseguro |
| 3. Segurança | Segredos, dados, identidade, RLS/RBAC e LGPD foram avaliados? | Testes negativos, scanner, grants/policies e checklist de dados | Segredo exposto, acesso excessivo ou tratamento sem decisão |
| 4. Custos | Quotas, free tier, storage e pay-as-you-go foram avaliados? | Premissas datadas, fontes oficiais, consumo/limites | Custo ilimitado, premissa ausente ou limite desconhecido crítico |
| 5. Testes | Comportamento, falhas, idempotência e limites foram testados? | Suíte relacionada e resultado registrado | Falha, skip de cenário obrigatório ou teste sem assertiva útil |
| 6. Operação | Health, logs, alertas, owner e runbook suportam a entrega? | Simulação de falha/recuperação e procedimento | Falha silenciosa ou ninguém responsável por responder |
| 7. Documentação | README, plano, risco, runbook e rastreabilidade refletem o real? | Links válidos e check-docs | Afirmação incompatível com código/evidência |
| 8. Rollback | É possível interromper/reverter/recuperar sem operação destrutiva? | Plano testável, último válido e backup/checkpoint quando aplicável | Sem recuperação, alvo incerto ou comando proibido |
| 9. Validação humana | O responsável aprovou o resultado e as pendências? | Registro de revisão/aceite com data e escopo | Aprovação ausente para gate obrigatório |

## Evidências específicas por fase

Todos os nove gates se aplicam a todas as fases. A tabela destaca a prova que diferencia cada fase; ela não reduz os gates universais.

| Fase | Requisitos | Arquitetura | Segurança | Custos | Testes | Operação | Documentação | Rollback | Validação humana |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0. Fundação | baseline e STORE-04 rastreados | 5 tabelas sem divergência | catálogo de RLS/grants | consumo staging conhecido | unit, lint e integração exigida | Data API/health verificados | architecture/testing/run log | histórico e transação conferidos | SQL e ambiente aprovados |
| 1. Google | ING-01/03 aceitos | conector na borda | Service Account mínima, sem segredo | quota/chamadas documentadas | real fictício + 401/403/404/429/timeout | retry e atraso visíveis | quota/runbook atualizados | revogar credencial/pausar fonte | acesso Google aprovado |
| 2. Raw/sync | STORE-02/AVAIL-01 | raw, run e espelho coerentes | PII e acesso raw avaliados | storage por carga medido | 1ª/2ª, add/change/delete/restore | contagens e último válido | workflow/runbook | transação/checkpoint/restore | reconciliação aprovada |
| 3. Drift | PROC-01/02 | contratos e gate aditivo | payload de erro minimizado | custo de reprocessamento avaliado | drift e isolamento multi-fonte | pedido de mudança consultável | política de schema | snapshot não avança | mudança estrutural revisada |
| 4. Analítico | STORE-01/03 | grain, fatos e dimensões | PII minimizada na camada | capacidade/custo comparados | SQL, reconciliação e performance | refresh observável | métricas e ADR | rebuild a partir de raw | negócio valida métricas |
| 5. BI/RLS | STORE-04/WF-06 | conexão e escopos definidos | testes positivos/negativos | free tier e usuários avaliados | perfis e carga do dashboard | falha/latência visíveis | matriz de acesso | revogar conexão/reverter policy | Segurança e negócio aprovam |
| 6. Alertas | PROC-03/04 | eventos, saúde e canal | sem payload/segredo no alerta | volume/custo de mensagens | falha, dedupe e recuperação | owner/escalonamento ativos | runbook/SLO | silenciar com controle e canal alternativo | Operações confirma recebimento |
| 7. Viabilidade | COST/CLIENT/TECH | planos A/B/C coerentes | LGPD, credenciais e backup | cenários/base/pico aprovados | onboarding/backfill/restore fictícios | responsabilidades definidas | políticas e fontes datadas | contingência por camada | Empresa decide pendências |
| 8. Draw.io | WF-01–08 | diagrama corresponde ao real | risco em cada etapa | limite em cada etapa | checklist de correspondência | operação transversal visível | `.drawio` + exportação | caminhos de contingência visíveis | técnica e Diretoria revisam |

## Checkpoint da Fase 0 em 2026-08-06

| Gate | Resultado | Evidência ou pendência |
| --- | --- | --- |
| 1. Requisitos | aprovado | matriz mantém 40 requisitos e registra os seis itens afetados sem elevar status indevidamente |
| 2. Arquitetura | aprovado | migration local/remota convergente; cinco tabelas e relacionamentos coerentes |
| 3. Segurança | aprovado no alcance da fundação | RLS nas cinco, zero policies, frontend sem grants, backend autorizado e nenhuma linha |
| 4. Custos | aprovado com restrição | tamanhos atuais inspecionados; custos futuros continuam na Fase 7 |
| 5. Testes | aprovado com restrição | suíte offline obrigatória executada; integração local continua pulada sem Docker/`psql` |
| 6. Operação | aprovado no alcance da fundação | Data API HTTP 200; nenhuma ingestão ou scheduler pertence à Fase 0 |
| 7. Documentação | aprovado | estado remoto reconciliado sem apagar a tentativa falha e o rollback |
| 8. Rollback | aprovado no alcance inspecionado | histórico registra rollback da primeira tentativa; nenhuma escrita ocorreu nesta validação |
| 9. Validação humana | pendente | revisão humana deste checkpoint e das alterações documentais |

Estado técnico remoto: `baseline_applied_validated`. A classificação não equivale a validar RLS/RBAC hierárquico ou as fases posteriores.

## Checkpoint local da Fase 1 em 2026-08-06

| Gate | Resultado | Evidência ou pendência |
| --- | --- | --- |
| 1. Requisitos | aprovado com restrição | `ING-03` agora é `implemented_not_validated`; acesso real continua aberto |
| 2. Arquitetura | aprovado localmente | domínio tipado, transporte estreito injetável e nenhuma dependência de Supabase/SQL |
| 3. Segurança | aprovado localmente | escopo único read-only, credencial fora do repositório, fixture confirmada por humano e logs allowlist; rotação real pendente |
| 4. Custos | aprovado com restrição | quotas oficiais e duas chamadas/execução documentadas; volume/frequência e mudança comercial de 2026 permanecem abertas |
| 5. Testes | aprovado localmente | 29 cenários Google offline; autenticação, 401 real e leitura real não executadas |
| 6. Operação | aprovado com restrição | retry, métricas locais e runbook existem; sem centralização, scheduler ou evento real |
| 7. Documentação | aprovado | limites, segurança, riscos, plano e rastreabilidade atualizados |
| 8. Rollback | aprovado no alcance | revogar compartilhamento/chave e pausar a fonte; nenhuma escrita Google/Supabase existe |
| 9. Validação humana | pendente | revisão das mudanças e confirmação da fixture antes do diagnóstico real |

A Fase 1 não está concluída. Próximo gate único: executar `verify-google-sheets.py --confirm-fictitious` no `.venv` após revisão humana da planilha privada.

## Checkpoint remoto da Fase 1 em 2026-08-06

| Gate | Resultado | Evidência ou pendência |
| --- | --- | --- |
| 1. Requisitos | reprovado para saída | `ING-03` continua `implemented_not_validated`; nenhum metadado foi lido |
| 2. Arquitetura | aprovado | somente transporte GET na borda; nenhuma referência a Supabase/SQL |
| 3. Segurança | aprovado com restrição | fixture confirmada, escopo read-only, token em memória e saída sanitizada; autorização incoerente pendente |
| 4. Custos | inconclusivo | três GETs de metadados são irrelevantes para capacidade; nenhuma carga ocorreu |
| 5. Testes | local aprovado, remoto reprovado | 29 testes Google offline passam; diagnóstico e teste opt-in recebem 403 |
| 6. Operação | reprovado | falha visível e sem retry indevido, mas leitura não está operacional |
| 7. Documentação | aprovado | falha e pendências registradas sem identificadores |
| 8. Rollback | aprovado | nenhuma escrita ou mudança de permissão; nada a reverter |
| 9. Validação humana | parcial | natureza fictícia/privada confirmada; acesso técnico precisa de revisão externa |

A Fase 1 permanece aberta. Próximo gate único: revisar habilitação da API, identidade compartilhada e fixture configurada, sem expor valores, e repetir o diagnóstico read-only. A Fase 2 não foi iniciada.

## Checkpoint remoto aprovado da Fase 1 em 2026-08-06

| Gate | Resultado | Evidência ou pendência |
| --- | --- | --- |
| 1. Requisitos | aprovado com restrição | `ING-03` avançou para `partially_validated`; escopo limitado à fixture fictícia |
| 2. Arquitetura | aprovado | leitor e transporte permaneceram independentes do Supabase |
| 3. Segurança | aprovado | Service Account read-only, token em memória, fixture fictícia e saída sanitizada |
| 4. Custos | aprovado com restrição | uma leitura real de 7 colunas/5 linhas; quotas e escala futura continuam abertas |
| 5. Testes | aprovado | diagnóstico real e teste opt-in passaram; suíte local permanece verde |
| 6. Operação | aprovado com restrição | duração/retries/contagens observados; sem scheduler, centralização ou persistência |
| 7. Documentação | aprovado | histórico do 403 preservado e sucesso documentado |
| 8. Rollback | aprovado | nenhuma escrita ocorreu; não há alteração remota a reverter |
| 9. Validação humana | aprovado para a fixture | dados fictícios, compartilhamento de Leitor e habilitação da API confirmados |

A Fase 1 pode ser encerrada no escopo da leitura da fixture privada fictícia. O próximo marco é a Fase 2, que exigirá gates próprios antes de qualquer escrita no Supabase.

## Checkpoint local da Fase 2A em 2026-08-06

| Gate | Resultado | Evidência ou pendência |
| --- | --- | --- |
| 1. Requisitos | aprovado com restrição | `STORE-02`/`AVAIL-01` receberam evidência local, sem promoção ampla |
| 2. Arquitetura | aprovado | domínio raw, serviço local e repositório PostgreSQL estão separados |
| 3. Segurança | aprovado com restrição | fixture fictícia, hashes sanitizados e zero payload persistido; LGPD/retenção abertas |
| 4. Custos | inconclusivo | 5 linhas não dimensionam storage ou retenção |
| 5. Testes | aprovado localmente | 18 cenários raw offline e dry-run real aprovados |
| 6. Operação | aprovado com restrição | lock, rollback e métricas existem localmente; sem health persistido |
| 7. Documentação | aprovado | ADR de semântica raw e lacuna de schema registrados |
| 8. Rollback | aprovado no alcance local | falha preserva snapshot local; nenhum remoto foi alterado |
| 9. Validação humana | pendente | migration incremental e futura escrita exigem aprovação separada |

Naquele checkpoint de 2026-08-06, a Fase 2A estava concluída somente localmente e a Fase 2B permanecia bloqueada pela incompatibilidade do schema raw então existente. Esse estado foi superado pelos checkpoints integrados posteriores.

## Checkpoint da migration incremental de estado raw em 2026-08-06

| Gate | Resultado | Evidência ou pendência |
| --- | --- | --- |
| 1. Requisitos | aprovado com restrição | `STORE-02` e `AVAIL-01` receberam evidência de DDL e de rollback local; nenhum status amplo avançou |
| 2. Arquitetura | aprovado | ADR registra a separação histórico/estado; `raw_state` isola as transições e a baseline permanece intacta |
| 3. Segurança | aprovado com restrição | RLS, zero policies, `anon`/`authenticated` sem grant e backend sem `delete`; retenção, anonimização e base legal continuam abertas |
| 4. Custos | inconclusivo | o crescimento do histórico depende da decisão sobre anexar observações inalteradas; nenhum volume real foi medido |
| 5. Testes | aprovado localmente, reprovado em banco real | 141 testes offline, 136 aprovados e 5 pulados; o DDL não foi executado em PostgreSQL porque Docker e `psql` estão ausentes |
| 6. Operação | aprovado com restrição | runbook cobre a migration não aplicada e o tombstone versus LGPD; sem execução operacional |
| 7. Documentação | aprovado | arquitetura, segurança, testes, runbook, roadmap, riscos, rastreabilidade e run log atualizados |
| 8. Rollback | aprovado no alcance local | falhas de histórico, de estado e de finalização preservam a versão anterior; nada foi alterado remotamente |
| 9. Validação humana | pendente | revisão do DDL e autorização da aplicação não foram concedidas |

No estado documentado por este checkpoint de 2026-08-06, a migration estava criada e **não aplicada**. O bloqueio foi superado pelas aplicações e sincronizações controladas posteriores; consulte o estado atual no início deste documento.

## Follow-up PostgreSQL local em 2026-08-11

O DDL foi executado e testado em PostgreSQL local real: catálogo, PK/FKs/CHECKs, UNIQUE, RLS, zero
policies, estados idempotentes, rollback e advisory lock concorrente passaram. As fixtures foram
revertidas. A suíte offline passou (141 testes, 136 aprovados, 5 pulados) e o remoto em modo
leitura/dry-run mostrou uma pendência e lint limpo. O gate continua **reprovado** porque
`service_role` tem DELETE efetivo em `raw_current_rows`, contrário ao menor privilégio esperado.
O aceite para staging requer uma migration incremental corretiva e repetição do teste de grants.

## Correção de grants em 2026-08-11

A mesma migration pendente foi corrigida (nenhuma terceira migration): REVOKE explícito removeu o
ACL herdado de PUBLIC, anon, authenticated e service_role, seguido do grant mínimo. O reset local,
as verificações de catálogo e testes por role aprovaram todos os privilégios positivos e negativos.
Com regressão raw, suíte, lint e dry-run verdes, o gate local está **aprovado para staging**;
permanece pendente apenas a autorização humana de aplicação.

## Resultado permitido do gate

- **Aprovado:** toda evidência obrigatória existe e as pendências não comprometem o aceite.
- **Aprovado com restrição:** somente pendência explicitamente fora do alcance da fase, com owner/prazo/risco; não permite marcar requisito mais amplo como `validated`.
- **Reprovado:** qualquer condição de bloqueio ocorreu. A fase permanece aberta.

Skips de integração contam como informação, não como aprovação do comportamento pulado. Evidência documental de execução anterior não substitui repetição quando o ambiente ou requisito mudou.

## Deploy da migration incremental no staging em 2026-08-11

Com autorização humana, somente `20260806120000_add_raw_current_state.sql` foi aplicada. O
histórico ficou convergente e a inspeção read-only confirmou DDL, constraints, RLS, zero policies,
grants mínimos e tabelas operacionais vazias. A Fase 2B não foi executada; seu próximo gate é uma
sincronização controlada de fixture exclusivamente fictícia, sob autorização separada.

## Gate event-only local em 2026-08-11

A terceira migration, o driver Python e a unidade transacional passaram no Supabase local. O diff
definitivo ocorre sob advisory lock; eventos e estado compartilham commit/rollback. Ciclo completo,
quatro falhas controladas e concorrência por fonte passaram. O gate está aprovado para staging,
mas nenhuma migration ou sincronização foi aplicada remotamente nesta etapa.

## Deploy validado no staging: migration event-only (2026-08-11)

Foi aplicado exclusivamente `20260811150000_make_raw_import_event_only.sql`.
O historico remoto/local ficou em 3/3, sem pendencias ou divergencias. A
introspecao de catalogo confirmou o schema event-only, a UNIQUE logica, a
ausencia da UNIQUE por posicao, RLS e grants sem regressao. As tabelas
operacionais estavam vazias; nao houve leitura Google, fixture ou DML de dados.

Classificacao: `deployed_validated`. Proximo checkpoint: primeira
sincronizacao integrada controlada da fixture ficticia.

## Integracao Google para staging interrompida (2026-08-11)

Fixture ficticia lida com 5 linhas e 7 colunas; dry-run com 5 novos estados e
5 eventos insert. A conexao PostgreSQL direta falhou antes de lock e
transacao. Contagens remotas seguiram zeradas. Classificacao: `blocked`;
proximo checkpoint unico: conectividade direta para o adaptador transacional.

## Checkpoint de idempotência integrada no staging em 2026-08-13

| Gate | Resultado | Evidência sanitizada |
| --- | --- | --- |
| Leitura Google | aprovado | duas leituras read-only da fixture fictícia: 5 linhas, 7 colunas e zero retries |
| Primeira sincronização | aprovado | 1 fonte, 1 run aplicado, 5 estados novos e 5 eventos insert |
| Repetição idêntica | aprovado | 2 runs aplicados; 5 unchanged, zero novos eventos e versões preservadas em 1 |
| Atomicidade | aprovado | `psycopg`, Session Pooler, transação, advisory xact lock, diff sob lock e commit no caminho da aplicação |
| Integridade | aprovado | `import_errors=0`, tombstones/update/restore=0, RLS nas 6 tabelas e zero policies |
| Schema e regressão | aprovado | migrations 3/3 sem pendência/divergência, lint verde e 150 testes com 142 aprovados/8 pulados |

Classificação: `integrated_idempotency_validated`. Próximo gate único: autorização
específica para testar uma mudança controlada da fixture fictícia.

## Checkpoint de ciclo de mudanças no staging em 2026-08-17

| Cenário | Resultado | Evidência agregada |
| --- | --- | --- |
| Update | aprovado | 1 update; mesma identidade; versão 1 para 2 |
| Tombstone | aprovado | 1 tombstone; estado preservado e campos históricos nulos |
| Restore | aprovado | 1 restore; mesma identidade; versão 2 para 3 |
| Reorder | aprovado | 5 unchanged; zero evento e zero incremento de versão |
| Integridade | aprovado | 5 estados, 8 eventos, 6 runs aplicados, zero import_errors, migrations 3/3 e lint verde |

Classificação: `integrated_change_cycle_validated`. Próximo gate único:
autorização específica para schema drift controlado da fixture fictícia.

## Checkpoint parcial de schema drift em 2026-08-17

| Cenário | Resultado | Evidência agregada |
| --- | --- | --- |
| Coluna adicionada | aprovado | 7→8, bloqueio seguro e uma request pendente |
| Coluna removida | aprovado | 7→6, bloqueio antes de diff e request distinta |
| Rename | aprovado | drift genérico, sem equivalência automática e request distinta |
| Restaurações | aprovado | baseline 7 colunas, 5 unchanged e sem sync extra |
| Negócio | preservado | 5 estados, 8 eventos, 6 runs e zero import_errors |

Próximo gate único: reorder controlado de headers.

## Gate de desenho do schema de retenção em 2026-08-25

| Gate | Resultado | Evidência sanitizada |
| --- | --- | --- |
| Schema atual | aprovado | três migrations lidas offline; PKs, FKs, timestamps, status, current e history mapeados |
| Política por fonte | aprovado | valores em configuração externa versionada; policy e dry-run digests congelados na evidência |
| Legal hold | aprovado | hold institucional ou por fonte; registro individual adiado; hold sempre bloqueia purge/offboarding |
| Current e history | aprovado | current fora de purge histórico; history por idade, run terminal e janela de reconciliação |
| Runs e commit ambíguo | aprovado | runs referenciadas, não terminais ou dentro da janela permanecem; FK `last_sync_run_id` preservada |
| Offboarding | aprovado | lifecycle mínimo, sync parada, credenciais revogadas, aprovação, hold check e evidência final |
| Segurança | aprovado | duas novas tabelas conceituais, RLS, zero policies, grants mínimos e nenhuma PII adicional |
| Execução | não realizada | nenhuma migration, DDL, purge, Google, staging ou commit |

Classificação: `retention_schema_design_validated`. Próximo gate único: revisão
humana da ADR e autorização para criar somente localmente a migration 4 e seus
testes offline.

## Gate multi-source local em 2026-09-02

| Gate | Resultado | Evidencia sanitizada |
| --- | --- | --- |
| Configuracao | aprovado | duas fontes em `sources[]`, pares planilha/aba e mirrors distintos |
| Identidade e schema | aprovado | mesma key textual em namespaces distintos; schemas A e B diferentes sem drift cruzado |
| Estado e history | aprovado | primeira carga, idempotencia, update e tombstone/restore isolados por `data_source_id` |
| Drift | aprovado | request somente para A; B permaneceu valida |
| Lock | aprovado | A/A busy; B sincronizou enquanto A mantinha lock |
| Resiliencia | aprovado | rollback e retry de A nao alteraram B; lote continuou apos falha |
| Lifecycle e hold | aprovado | A inactive nao suspendeu B; hold especifico de A nao se aplicou a B |
| Observabilidade | aprovado | referencias seguras por fonte e resumo agregado sem payload ou identificador externo |
| Banco | aprovado | 25 testes PostgreSQL; migrations 4/4; nenhuma migration nova |

Classificacao: `multi_source_local_validated`. Nao houve acesso Google,
staging, scheduler ou purge. Proximo gate unico: definir o caso de negocio e o
contrato minimo da camada analitica.
