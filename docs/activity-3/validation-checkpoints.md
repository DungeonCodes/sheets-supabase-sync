# Checkpoints de validação da Atividade 3

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

A Fase 2A está concluída somente localmente. A Fase 2B está bloqueada pela incompatibilidade do schema raw atual; não criar ou aplicar migration é parte deste checkpoint.

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

A migration está criada e **não aplicada**. A Fase 2B permanece bloqueada; o gate 5 só poderá ser
fechado com execução do DDL em PostgreSQL real.

## Resultado permitido do gate

- **Aprovado:** toda evidência obrigatória existe e as pendências não comprometem o aceite.
- **Aprovado com restrição:** somente pendência explicitamente fora do alcance da fase, com owner/prazo/risco; não permite marcar requisito mais amplo como `validated`.
- **Reprovado:** qualquer condição de bloqueio ocorreu. A fase permanece aberta.

Skips de integração contam como informação, não como aprovação do comportamento pulado. Evidência documental de execução anterior não substitui repetição quando o ambiente ou requisito mudou.
