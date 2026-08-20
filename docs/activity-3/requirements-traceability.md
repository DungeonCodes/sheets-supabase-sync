# Rastreabilidade de requisitos da Atividade 3

Fonte oficial: [`docs/decisions/20260806_inicie_etl_clientes_orientacao.md`](../decisions/20260806_inicie_etl_clientes_orientacao.md).

Auditoria documental realizada em 2026-08-06. A fonte oficial permanece inalterada. Os resumos abaixo preservam sua terminologia e transformam afirmações e perguntas verificáveis em 40 requisitos estáveis.

Atualização de 2026-08-18: os checkpoints posteriores validaram o pipeline raw no staging com fixture fictícia para carga inicial, idempotência, update, tombstone, restore, reorder de linhas e migrations 3/3. Schema drift de coluna adicionada/removida e rename foi bloqueado antes de persistência; reorder de headers foi compatível por mapeamento por nome e header duplicado foi rejeitado pelo leitor. Entradas cronológicas anteriores que tratem a migration ou persistência como futuras devem ser lidas como histórico superado.

## Regras de classificação

- `validated`: há implementação, teste executável e documentação coerente; o alcance da evidência é indicado explicitamente.
- `partially_validated`: existe parte verificável, mas falta uma camada, integração ou prova exigida.
- `implemented_not_validated`: há preparação concreta, porém sem validação suficiente do comportamento solicitado.
- `planned`: não há implementação; existe trabalho definido.
- `blocked`: depende de decisão, acesso, volume, orçamento ou dado externo ainda não fornecido.
- `out_of_scope`: requisito conscientemente excluído do projeto. Nenhum requisito oficial foi classificado assim nesta auditoria.

## Checkpoint integrado de staging em 2026-08-13

Evidência posterior e sanitizada para `ING-03`, `STORE-02` e `AVAIL-01`:
duas leituras reais da fixture exclusivamente fictícia retornaram 5 linhas e 7
colunas. A primeira sincronização integrada criou uma fonte, 5 estados raw e 5
eventos insert; a repetição idêntica produziu 5 inalterados e zero eventos
adicionais. As versões permaneceram em 1, `import_errors=0` e as duas
execuções concluíram com sucesso sob transação e advisory lock. O alcance não
inclui alterações da fixture, drift, BI, retenção ou carga multi-fonte.

## Ciclo de mudanças integrado em 2026-08-17

O checkpoint posterior estende a evidência sanitizada de `STORE-02` e
`AVAIL-01`: update, tombstone, restore e reorder foram aplicados um por vez no
staging. Foram preservadas as identidades, as versões corretas e a ausência de
eventos por reorder; o alcance ainda exclui schema drift, carga multi-fonte,
retenção e BI.

## Checkpoint completo de schema drift em 2026-08-18

Para `PROC-01`, a integração bloqueia no staging headers adicionados, removidos
ou renomeados sem aprovação humana. Três requests pendentes distintas foram
registradas sem eventos de negócio, alterações de versão ou tombstones. Reorder
de headers preservou cinco inalterados sem request adicional; header duplicado
foi rejeitado pelo leitor antes da transação. A fixture retornou à baseline.

## 1. Objetivo geral

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OBJ-01 | Substituir fórmulas Google Sheets e Apps Script por arquitetura ETL/ELT escalável, estável e de custo zero. | `partially_validated` | pipeline Google read-only → raw staging validado com fixture fictícia; `src/`; `tests/`; `docs/architecture.md` | Não há operação multi-fonte, camada analítica ou prova de custo. | MVP ponta a ponta repetível, metas de escala medidas e custo/free tier documentado. | crítica | Fases 0–7; decisões OD-01 a OD-03 e OD-10 | R-01, R-02, R-03, R-13 |
| OBJ-02 | Extrair e transformar dados de forma robusta e disponibilizá-los em dashboards analíticos de alto desempenho. | `partially_validated` | conector Google read-only, snapshot/diff e raw staging validados | Transformação analítica, BI e medição de dashboard ausentes. | Fonte fictícia real → raw → SQL → tabela analítica → consulta BI, com reconciliação e tempo medido. | crítica | Fases 1–5 | R-02, R-08, R-10, R-13 |
| OBJ-03 | Garantir proteção de dados sensíveis dos clientes. | `partially_validated` | Testes de segredo/host; em 2026-08-06 o catálogo confirmou RLS, grants restritos e zero policies nas tabelas operacionais | Retenção, minimização, anonimização, LGPD e acesso analítico não definidos. | Threat review, política LGPD/retention aprovada e testes de acesso negativo aprovados. | crítica | OD-07 a OD-09, Fases 5 e 7 | R-05, R-06, R-15 |

## 2. Desempenho e qualidade

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DQ-01 | Suportar volumes crescentes mantendo consultas e dashboards ágeis. | `partially_validated` | teste opt-in de snapshot com 10.000 linhas | O teste não define limite de tempo nem cobre banco, SQL analítico ou BI. | Volumes acordados testados com p95 e metas de carga/consulta aprovadas. | alta | OD-02, OD-03, Fases 4–5 | R-04, R-13 |
| DQ-02 | Maximizar tecnologias open-source, free tiers sustentáveis ou custo zero. | `partially_validated` | Python stdlib sem dependências de produção; PostgreSQL/Supabase | Não há pesquisa citada, sustentabilidade nem comparação de alternativas. | Matriz de ferramentas, limites atuais, premissas e gatilhos de upgrade revisados. | alta | Fase 7; pesquisa com fontes oficiais | R-01, R-03, R-16, R-18 |
| DQ-03 | Controle rigoroso de acesso e anonimização/tratamento em conformidade com LGPD. | `partially_validated` | isolamento por projeto; RLS e grants operacionais validados remotamente; artefatos sanitizados | Sem RLS por usuário, anonimização, base legal, retenção ou descarte. | Perfis distintos bloqueiam dados indevidos e política LGPD é aprovada e testada. | crítica | OD-06 a OD-09, Fases 5 e 7 | R-05, R-06, R-15 |
| DQ-04 | Código limpo e manutenível, com Python (ou equivalente) e SQL para tratamento. | `validated` | módulos pequenos e desacoplados; `pyproject.toml`; `sql_generator.py`; suíte comportamental; skill de manutenção | A avaliação de handoff diário ainda pertence a MAINT-01/02. | Compilação e testes aprovados; arquitetura e convenções documentadas sem dependência implícita. | alta | CI e revisão contínua | R-11 |

## 3. Ingestão e conectividade

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ING-01 | Mapear e gerir quotas/rate limits de Google Forms, Google Sheets e APIs. | `partially_validated` | `google-sheets-api-limits.md`; retry integrado com backoff, jitter, orçamento, `Retry-After`; testes 429/503/timeout | Sem rate limiter global, carga multi-fonte ou conferência da cota efetiva do projeto; Forms não foi avaliado. | Limites oficiais citados; orçamento de chamadas, backoff+jitter e teste de 429 integrados. | crítica | Fase 1; conector real | R-02, R-17 |
| ING-02 | Definir frequência: batch periódico ou evento quase em tempo real, alinhada ao cliente. | `partially_validated` | `sync_interval_minutes`, `due_sources` e exemplo de 180 min | Cadência empresarial e SLA não decididos; scheduler não implantado. | Decisão registrada, scheduler repetível e atraso máximo monitorado. | alta | OD-01, OD-03, OD-05 | R-08, R-13 |
| ING-03 | Capturar Google Forms/Sheets por webhooks, conectores Python ou APIs. | `partially_validated` | leitor/transporte HTTP v4 read-only; 29 testes offline; diagnóstico real encontrou a aba e leu 7 colunas/5 linhas em 2026-08-06 | Não há execução multi-fonte, scheduler ou validação Google Forms; a leitura real foi comprovada apenas para a fixture fictícia. | Planilha fictícia lida pela API real sem segredo exposto, com timeout e erros testados. | crítica | Fase 2; revisão de frequência | R-02, R-05, R-19 |

## 4. Processamento, qualidade e resiliência

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PROC-01 | Validar tipos e schema drift. | `partially_validated` | `contracts.py`, `diff.py`, `normalization.py`; testes e checkpoints integrados de coluna adicionada/removida e rename | Reorder de headers e header duplicado ainda exigem checkpoint humano; integração multi-fonte é posterior. | Cenários públicos continuam cobertos e qualquer drift bloqueante gera evidência sem alterar snapshot. | crítica | Fase 3 para validação integrada | R-07 |
| PROC-02 | Tratar exceções sem quebrar a execução total. | `validated` | `batch.synchronize_independently`; teste de falha de uma fonte com continuidade de outra; transação/rollback do adaptador validados | Falha operacional persistida e multi-fonte continuam pendentes. | Falha simulada de uma fonte não impede a seguinte e ambos os resultados ficam registrados. | crítica | Fases 1–3 | R-08 |
| PROC-03 | Centralizar monitoramento e logs, inclusive estouro de limite de API. | `partially_validated` | falha Google real registrada apenas como `authorization`, sem URL/ID/token/células; testes locais de tentativa/espera/contagens | Logs não são centralizados; duração de falha veio do comando, sem retenção ou evento real de quota. | Execuções e erros consultáveis centralmente, sanitizados e retidos conforme política. | alta | Fases 2 e 6; OD-08 | R-06, R-17 |
| PROC-04 | Executar rotinas automáticas e alertas por e-mail. | `planned` | regras determinísticas de severidade em `health.py` | Não há scheduler, transportador de e-mail, deduplicação ou aviso de recuperação. | Falha gera um e-mail; repetição é suprimida; recuperação gera notificação e evidência. | alta | Fase 6; OD-12 | R-17 |
| PROC-05 | Preferir pipelines legíveis e reutilizáveis, evitando complexidade excessiva. | `validated` | separação domínio/bordas; módulos curtos; dependências explícitas; testes offline | Deve permanecer gate contínuo. | Revisão não encontra módulos genéricos, estado global, dependência cíclica ou abstração sem uso. | média | Revisão por fase | R-11 |

## 5. Armazenamento, modelagem e segurança

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STORE-01 | Definir banco analítico/Data Warehouse com capacidade e escala sem degradação. | `planned` | PostgreSQL/Supabase foi escolhido apenas para base operacional | Não há decisão analítica, benchmark ou estimativa de capacidade. | ADR compara opções e benchmark comprova metas de volume/consulta. | alta | OD-02/03/10; Fases 4 e 7 | R-04, R-13, R-18 |
| STORE-02 | Receber dados puros em staging ou armazenamento bruto (raw data). | `partially_validated` | migrations 3/3, duas cargas idempotentes e ciclo de mudanças validados no staging com fixture fictícia | Retenção, minimização, multi-fonte e operação contínua permanecem indefinidas. | Duas cargas persistem raw auditável/idempotente e staging separada, com retenção testada. | crítica | Fases 2B, 4 e 7 | R-04, R-06, R-12, R-20 |
| STORE-03 | Transformar em SQL para Star Schema ou Snowflake, com fatos e dimensões. | `planned` | SQL atual é somente upsert de espelho operacional | Caso de negócio, staging, dimensões, fato, métricas e reconciliação ausentes. | Star Schema funcional, consultas testadas e métricas reconciliadas. | crítica | Fase 4; definição de caso de negócio | R-10, R-13 |
| STORE-04 | Aplicar controle hierárquico de visualização por RLS/RBAC. | `partially_validated` | catálogo remoto: RLS nas cinco tabelas operacionais, zero policies, `anon`/`authenticated` sem acesso e backend autorizado | Não há policies hierárquicas, papéis, escopo por usuário nem teste com identidades distintas. | Dois ou mais escopos demonstrados; consultas negativas não retornam dados indevidos. | crítica | OD-06; Fase 5; modelo de identidade | R-15 |

## 6. Workflow e fluxograma

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WF-01 | Pesquisar, testar e mapear ponta a ponta em fluxograma detalhado no Draw.io. | `planned` | `docs/workflow.md` é descrição textual parcial | Não há arquivo `.drawio`, exportação ou validação interna. | `.drawio` e PDF/PNG correspondem à arquitetura testada e são revisados. | alta | Fases 1–7; Fase 8 | R-11 |
| WF-02 | Mostrar fonte/ingestão Google Forms/Sheets e mecanismo de captura. | `planned` | Fluxo textual menciona Google futuro | Ausente no Draw.io e mecanismo não escolhido/testado. | Nó identifica fonte, mecanismo, ferramenta, risco e quota. | alta | ING-03 | R-02 |
| WF-03 | Mostrar staging ou armazenamento raw. | `planned` | Arquitetura textual e tabela raw operacional | Sem camada implementada ponta a ponta nem diagrama. | Nó raw/staging corresponde a tabelas e fluxo validados. | alta | STORE-02 | R-06 |
| WF-04 | Mostrar qualidade, schema drift e transformação SQL para Star Schema. | `planned` | Drift offline existente | Star Schema e diagrama ausentes. | Fluxo mostra gates de drift, erro e transformação executável. | alta | PROC-01, STORE-03 | R-07 |
| WF-05 | Mostrar armazenamento analítico otimizado. | `planned` | Nenhuma camada analítica definida | Ferramenta e modelo pendentes. | Nó referencia decisão e objeto analítico testado. | alta | STORE-01/03 | R-13 |
| WF-06 | Mostrar BI e filtros de segurança por nível de usuário (RLS). | `planned` | Nenhuma integração BI | Ferramenta, dashboard e perfis pendentes. | Conexão e filtros representados e comprovados por teste. | alta | OD-04/06; Fase 5 | R-10, R-15 |
| WF-07 | Mostrar camada transversal de logs e meio de alertas. | `planned` | Componentes locais de health/log | Armazenamento central e canal não existem. | Diagrama referencia logs reais e e-mail testado. | alta | PROC-03/04 | R-17 |
| WF-08 | Anotar ferramentas, segurança/vazamento e limitações operacionais/quota em cada etapa. | `planned` | Riscos aparecem dispersos na documentação | Não há anotação sistemática por etapa. | Todas as caixas contêm ferramenta, risco/controle e limite verificável. | alta | Pesquisa de custos/quotas e risk register | R-01, R-02, R-05 |

## 7. Custos e escalabilidade

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| COST-01 | Estimar infraestrutura se custo zero não for possível no longo prazo. | `blocked` | Não há estudo | Faltam volume, frequência, retenção, SLA e orçamento. | Cenários base/pico com data, moeda, premissas e gatilhos aprovados. | alta | OD-01/02/03/08/10 | R-01, R-04, R-13, R-16 |
| COST-02 | Registrar limites exatos dos planos gratuitos de cada ferramenta. | `planned` | Não há tabela atualizada nem fontes | Requer pesquisa temporal em documentação oficial. | Tabela datada, citada, com unidade, janela e comportamento no excedente. | crítica | Fase 7; ferramentas escolhidas | R-01, R-03 |
| COST-03 | Avaliar risco de cobrança pay-as-you-go descontrolada em picos. | `planned` | Guardrails de custo não documentados | Sem modelo de consumo, alertas ou limites de gasto. | Política de budget/cap/alerta e simulação de pico documentadas. | alta | COST-01/02; OD-10 | R-16 |

## 8. Impacto no cliente e onboarding

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CLIENT-01 | Definir softwares, contas e permissões exigidos do cliente. | `blocked` | Arquitetura prevê projeto isolado e Service Account futura | Fluxo de consentimento e responsabilidades não decidido. | Checklist aprovado lista ator, conta, permissão mínima e revogação. | alta | OD-11/14; decisão de ferramentas | R-09, R-15 |
| CLIENT-02 | Definir onboarding e migração do histórico. | `blocked` | Não há procedimento | Faltam responsável, formato, volume, janela e validação do cliente. | Ensaio com dados fictícios cobre preparação, carga, reconciliação e aceite. | alta | OD-02/11; Fases 1–4 | R-09, R-13 |
| CLIENT-03 | Definir passo a passo para carregar histórico de cliente novo ou antigo. | `blocked` | Não há runbook específico | Estratégia de backfill, checkpoint e rollback depende do caso. | Runbook versionado e teste de repetição sem duplicação aprovados. | alta | CLIENT-02; OD-11 | R-09 |

## 9. Dependência tecnológica

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TECH-01 | Identificar substitutos equivalentes se ferramenta gratuita mudar ou for descontinuada. | `planned` | ADR de Supabase não traz matriz de substituição | Critérios de equivalência e teste de portabilidade ausentes. | Alternativas por camada com esforço, perda funcional e gatilho de troca. | média | Fase 7; arquitetura-alvo | R-03, R-18 |
| TECH-02 | Listar ferramentas aplicadas e planos B e C. | `planned` | Stack atual documentada, sem planos B/C | Alternativas não pesquisadas/testadas. | Matriz cobre ingestão, orquestração, banco, BI, alertas e segredos. | alta | TECH-01, COST-02 | R-03, R-18 |

## 10. Disponibilidade e contingência

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AVAIL-01 | Em falha de servidor/API/dashboard, exibir último dado válido em vez de tela de erro. | `partially_validated` | snapshot local só avança após commit; falhas simuladas de início/commit/finalização restauram o último snapshot local | Sem estado raw remoto, tabela analítica/dashboard, backup ou teste de indisponibilidade. | Falha simulada mantém consulta BI no último conjunto reconciliado e registra recuperação. | crítica | migration incremental; Fases 2B, 5 e 6; OD-13/15 | R-08, R-09, R-10, R-12, R-20 |

## 11. Segurança, credenciais e LGPD

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Definir armazenamento de credenciais, chaves de API e senhas dos bancos dos clientes. | `partially_validated` | credencial externa e estruturalmente válida; escopo read-only; requisição real sem exposição de token/e-mail/ID; procedimento de revogação | Não há secret manager, rotação exercitada, owner ou auditoria; autorização da fixture segue pendente. | ADR e runbook definem cofre, mínimo privilégio, rotação, expiração e resposta a incidente. | crítica | OD-14; Fases 1 e 7 | R-05, R-19 |
| SEC-02 | Garantir que senhas e chaves não fiquem em código aberto ou scripts locais. | `validated` | varredura/testes; credencial fora do repositório; três falhas GET reais exibiram somente categoria sanitizada | Gate deve permanecer contínuo e ampliar cobertura conforme novos formatos. | CI e revisão não detectam segredo; credenciais reais permanecem fora de Git e artefatos. | crítica | CI; gestão de credenciais | R-05 |

## 12. Manutenibilidade e continuidade

| ID | Requisito original resumido | Status | Evidência | Lacuna | Critério de aceite | Prioridade | Dependências | Risco |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAINT-01 | Avaliar o nível de complexidade da manutenção diária. | `implemented_not_validated` | módulos pequenos, doctor, runbook, testes e CI | Não há catálogo de rotinas, estimativa de esforço, SLO operacional ou exercício de incidente. | Operador externo executa rotina e incidente fictício com tempo e lacunas registrados. | média | Fases 6–8 | R-11, R-17 |
| MAINT-02 | Permitir manutenção por outro profissional com conhecimentos básicos de Python. | `implemented_not_validated` | arquitetura desacoplada, documentação, fixtures e testes offline | Não houve handoff independente nem avaliação de bus factor. | Profissional não autor executa setup, teste, diagnóstico e correção guiada sem segredo. | alta | Documentação final; validação humana | R-11 |

## Checkpoint remoto de 2026-08-06

Inspeção somente de leitura classificou a fundação como `baseline_applied_validated`. Nenhum dos 40 status amplos mudou: a evidência de fundação ficou mais forte, mas não comprova RLS/RBAC hierárquico, ingestão raw integrada, LGPD ou operação.

| Requisito | Status anterior | Nova evidência | Status atual | Gate ainda aberto | Próximo teste necessário |
| --- | --- | --- | --- | --- | --- |
| `OBJ-03` | `partially_validated` | RLS/grants operacionais e ausência de policies confirmados no catálogo | `partially_validated` | LGPD e acesso analítico | teste negativo com perfis da camada analítica |
| `DQ-03` | `partially_validated` | isolamento, RLS e grants da fundação confirmados | `partially_validated` | anonimização, retenção e hierarquia | política LGPD e teste por escopo |
| `PROC-03` | `partially_validated` | tabelas operacionais de runs/erros existem e estão vazias | `partially_validated` | persistência e centralização em runtime | falha real fictícia registrada e consultada |
| `STORE-02` | `partially_validated` | tabela raw, colunas e constraints existem; zero linhas | `partially_validated` | escrita raw e staging | duas cargas fictícias idempotentes |
| `STORE-04` | `partially_validated` | RLS nas cinco; zero policies; frontend sem grants; backend autorizado | `partially_validated` | RLS/RBAC hierárquico | identidades fictícias com escopos distintos |
| `SEC-01` | `partially_validated` | staging e Data API verificados sem expor credencial | `partially_validated` | cofre, rotação e owner | exercício de rotação/revogação |

## Checkpoint local da Fase 1 em 2026-08-06

Implementação e testes offline não comprovam acesso ao serviço Google. Somente `ING-03` mudou de status porque deixou de ser apenas planejamento; o gate remoto permanece aberto.

| Requisito | Status anterior | Nova evidência | Status atual | Gate ainda aberto | Próximo teste necessário |
| --- | --- | --- | --- | --- | --- |
| `ING-01` | `partially_validated` | quotas oficiais datadas; backoff+jitter, `Retry-After` e orçamento integrados; testes 429/503 | `partially_validated` | cota efetiva, concorrência e rate limiter global | leitura real e carga multi-fonte fictícia |
| `ING-02` | `partially_validated` | custo de duas leituras por execução documentado | `partially_validated` | frequência/SLA empresarial e scheduler | decisão OD-01/03 e teste de cadência |
| `ING-03` | `planned` | Service Account oficial, transporte HTTP GET, leitor tipado e testes offline | `implemented_not_validated` | autenticação e leitura real fictícia | diagnóstico com confirmação humana |
| `PROC-03` | `partially_validated` | eventos locais allowlist para retry e resultado; teste sem ID/célula | `partially_validated` | runtime real, centralização e retenção | capturar métricas sanitizadas da fixture |
| `SEC-01` | `partially_validated` | arquivo externo obrigatório, escopo único, token em memória e revogação documentada | `partially_validated` | cofre, owner e rotação real | autenticar e depois exercitar revogação controlada |
| `SEC-02` | `validated` | testes garantem ausência de ID/célula/segredo em logs e exceções | `validated` | gate contínuo no diagnóstico real | varredura e revisão da saída real |

## Checkpoint de integração Google em 2026-08-06

A revisão humana confirmou fixture privada, exclusivamente fictícia e compartilhada como Leitor. A credencial externa obteve contexto suficiente para chamar a Sheets API, mas o GET inicial de metadados retornou HTTP 403 classificado como `authorization`. Nenhum metadado, cabeçalho ou valor foi retornado. Os status amplos permanecem conservadores.

| Requisito | Status anterior | Nova evidência real | Status atual | Gate ainda aberto | Próximo teste necessário |
| --- | --- | --- | --- | --- | --- |
| `ING-01` | `partially_validated` | uma chamada por execução, sem retry no 403; quota não foi consumida em volume relevante | `partially_validated` | 429/carga real e cota efetiva | leitura autorizada e carga multi-fonte |
| `ING-02` | `partially_validated` | fixture única não permite medir frequência ou SLA | `partially_validated` | decisão empresarial e scheduler | execução repetida na cadência aprovada |
| `ING-03` | `implemented_not_validated` | token em memória e GET real; API respondeu 403 antes dos metadados | `implemented_not_validated` | acesso à planilha/aba e leitura | revisão externa de autorização e novo diagnóstico |
| `PROC-03` | `partially_validated` | categoria real `authorization` registrada sem payload ou identificador | `partially_validated` | métricas de sucesso e centralização | leitura autorizada com contagens sanitizadas |
| `SEC-01` | `partially_validated` | credencial externa, escopo único e token não exposto em falha real | `partially_validated` | cofre/rotação/owner e autorização coerente | revisão de identidade e exercício de revogação |
| `SEC-02` | `validated` | saída real e traceback não contiveram segredo, URL, ID ou célula | `validated` | controle contínuo | repetir scanner após sucesso |

## Checkpoint de integração Google aprovado em 2026-08-06

Após a habilitação da Sheets API e o ajuste do nome da aba, o diagnóstico real executou com a fixture privada e fictícia confirmada. A API autenticou, a planilha ficou acessível, a aba foi localizada e a leitura retornou 7 colunas e 5 linhas. A saída permaneceu sanitizada; nenhum conteúdo de célula foi exibido.

| Requisito | Status anterior | Nova evidência real | Status atual | Gate ainda aberto | Próximo teste necessário |
| --- | --- | --- | --- | --- | --- |
| `ING-01` | `partially_validated` | execução real sem retry e dentro do orçamento; quotas não foram excedidas | `partially_validated` | rate limiter global, 429 real e carga multi-fonte | teste de carga fictício |
| `ING-02` | `partially_validated` | duração real de aproximadamente 1,9 s para uma execução | `partially_validated` | frequência/SLA empresarial e scheduler | decisão de cadência e teste repetido |
| `ING-03` | `implemented_not_validated` | autenticação, planilha, aba, cabeçalho e linhas comprovados em leitura real | `partially_validated` | Forms, múltiplas fontes e operação contínua | integração de uma segunda fixture fictícia |
| `PROC-03` | `partially_validated` | métricas reais sanitizadas: 7 colunas, 5 linhas, zero vazias, zero retries | `partially_validated` | centralização e retenção | persistir execução somente na Fase 2 |
| `SEC-01` | `partially_validated` | escopo read-only e leitura real sem exposição de token/ID/células | `partially_validated` | cofre, owner e rotação | exercício de revogação controlada |
| `SEC-02` | `validated` | diagnóstico real permaneceu sanitizado | `validated` | controle contínuo | scanner após cada execução |

## Checkpoint local da Fase 2A em 2026-08-06

| Requisito | Status anterior | Nova evidência | Status atual | Gate ainda aberto | Próximo teste necessário |
| --- | --- | --- | --- | --- | --- |
| `STORE-02` | `partially_validated` | dry-run real: 5 linhas, 5 novas e zero persistidas; contrato raw e incompatibilidade do schema testados | `partially_validated` | migration incremental, duas escritas e retenção | Fase 2B controlada após autorização |
| `AVAIL-01` | `partially_validated` | rollback local preserva snapshot em falhas de início/commit/finalização | `partially_validated` | último válido remoto e camada servida | rollback transacional no staging autorizado |
| `PROC-02` | `validated` | lock local recusa concorrência sem espera indefinida | `validated` | advisory lock PostgreSQL não executado | teste local de banco após migration |
| `PROC-03` | `partially_validated` | dry-run registra somente contagens, hashes e duração sanitizados | `partially_validated` | retenção e centralização | execução controlada persistida |
| `SEC-01` | `partially_validated` | payload raw não foi logado; ADR explicita PII/retenção pendentes | `partially_validated` | classificação, cofre e política LGPD | revisão de retenção antes de escrita |

## Checkpoint da migration incremental de estado raw em 2026-08-06

A migration `20260806120000_add_raw_current_state.sql` foi criada, coberta por testes offline e
aprovada em `migration list`, `db lint --linked` e `db push --dry-run`. Ela **não** foi aplicada e o
DDL **não** foi executado em PostgreSQL real. Nenhum status amplo avança por criação de DDL.

Follow-up em 2026-08-11: o PostgreSQL local confirmou o DDL e seus comportamentos transacionais,
mas revelou DELETE efetivo para `service_role` em `raw_current_rows`. Assim, a evidência reduz o
risco de aplicação do DDL, mas não altera os requisitos amplos: uma migration corretiva de menor
privilégio continua obrigatória antes de qualquer escrita em staging.

Correção em 2026-08-11: a mesma migration pendente passou a revogar o ACL herdado e foi reaplicada
somente no PostgreSQL local. Os testes de grants positivos e negativos, rollback e advisory lock
passaram; o gate específico da migration está aprovado para staging, sem alterar os requisitos
amplos de LGPD, retenção ou RBAC hierárquico.

Deploy em 2026-08-11: a migration foi aplicada ao staging permitido e o catálogo read-only
confirmou tabela, constraints, RLS, zero policies, grants mínimos e zero linhas. `STORE-02`
permanece `partially_validated`: a persistência por sincronização controlada ainda não ocorreu.

Gate de integração em 2026-08-11: a semântica event-only exige tombstone no histórico, mas o
CHECK aplicado o rejeita e a chave por linha física é ambígua para ausências inferidas. `STORE-02`,
`AVAIL-01` e `PROC-02` não avançam para escrita integrada até evolução de schema e adaptador
transacional locais, conforme ADR 20260811.

Follow-up local de 2026-08-11: a terceira migration e o adaptador transacional foram exercitados em
PostgreSQL real. Event-only, rollback e lock por fonte passaram; os requisitos permanecem parciais
até aplicação autorizada da migration e sincronização fictícia no staging.

| Requisito | Status anterior | Nova evidência | Status atual | Gate ainda aberto | Próximo teste necessário |
| --- | --- | --- | --- | --- | --- |
| `STORE-02` | `partially_validated` | DDL de estado atual com identidade por fonte/chave, tombstone, versão e índices; 37 testes offline de migration e estado | `partially_validated` | aplicação autorizada, duas escritas reais e retenção | aplicar em ambiente autorizado e reconciliar duas cargas |
| `AVAIL-01` | `partially_validated` | rollback local cobre falha de histórico, de estado e de finalização preservando a versão anterior | `partially_validated` | último válido remoto e camada servida | rollback transacional em PostgreSQL real |
| `PROC-02` | `validated` | lock local recusa concorrência; `pg_try_advisory_xact_lock` permanece declarado e não executado | `validated` | advisory lock PostgreSQL não executado | teste local de banco após aplicação |
| `STORE-04` | `partially_validated` | nova tabela nasce com RLS, zero policies, `anon`/`authenticated` sem grant e backend sem `delete` | `partially_validated` | RLS/RBAC hierárquico | identidades fictícias com escopos distintos |
| `DQ-03` | `partially_validated` | análise explícita de tombstone versus exclusão LGPD e de retenção por camada | `partially_validated` | base legal, retenção e anonimização | política aprovada e procedimento de descarte testado |
| `SEC-01` | `partially_validated` | DDL sem segredo; grants mínimos ao backend | `partially_validated` | cofre, rotação e owner | exercício de revogação controlada |

## Totais desta auditoria

| Status | Quantidade |
| --- | ---: |
| `validated` | 5 |
| `partially_validated` | 13 |
| `implemented_not_validated` | 3 |
| `planned` | 15 |
| `blocked` | 4 |
| `out_of_scope` | 0 |
| **Total** | **40** |

## Continuidade: deploy event-only no staging (2026-08-11)

A migration incremental `20260811150000_make_raw_import_event_only.sql` foi
aplicada isoladamente ao staging apos preflight e dry-run. A validacao
somente-leitura confirmou eventos `insert/update/tombstone/restore`, UNIQUE
`(sync_run_id, data_source_id, row_key_hash)`, remocao da unicidade fisica e
representacao de tombstone sem posicao, hash ou payload inventados. Nao houve
leitura Google, sincronizacao ou dados nas tabelas operacionais.

## Tentativa de integracao controlada (2026-08-11)

A leitura da fixture ficticia e o plano de 5 inserts passaram. A conexao
PostgreSQL direta ao staging falhou antes da transacao, portanto nao houve
persistencia, evento ou sync_run. STORE-02 permanece parcialmente validado ate
que a conectividade do adaptador seja disponibilizada.
