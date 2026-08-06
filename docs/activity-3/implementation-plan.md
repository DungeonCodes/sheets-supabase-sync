# Plano de implementação da Atividade 3

Plano incremental derivado da [matriz oficial](requirements-traceability.md). Nenhuma fase é concluída apenas por existir código; aplicam-se os [checkpoints obrigatórios](validation-checkpoints.md).

## Sequência de marcos

1. Fundação reconciliada em 2026-08-06: aplicação registrada, catálogo, RLS, grants, Data API e ausência de dados comprovados somente por leitura.
2. Fase 1 implementada e validada offline; tentativa real em 2026-08-06 recebeu 403. Próximo gate único: **revisar externamente a autorização e repetir a leitura read-only**.
3. O marco posterior continua sendo o MVP ponta a ponta fictício; a escrita raw não foi iniciada.

## Fase 0 — Fundação e banco

**Objetivo:** concluir a aplicação/validação da baseline no staging, validar tabelas operacionais, RLS, grants, Data API e estabilizar migrations.

**Entregáveis:** evidência sanitizada do histórico remoto; inventário das cinco tabelas; consultas de catálogo para RLS/grants/constraints; resultado da Data API; relatório de divergência; procedimento de migration incremental.

**Dependências:** autorização humana explícita para qualquer escrita; acesso staging permitido; cliente PostgreSQL ou driver apenas para leitura; baseline imutável.

**Riscos:** ambiente errado, credencial exposta, divergência de histórico, alteração retroativa da baseline (R-05, R-08, R-09, R-15).

**Critérios de entrada:** revisão humana do SQL; alvo e Project Ref validados sem exposição; backup/rollback documentado; nenhuma migration concorrente.

**Critérios de saída:** migration registrada remotamente; cinco tabelas operacionais criadas; nenhuma divergência; testes aprovados; nenhuma informação real inserida; RLS/grants/Data API comprovados.

**Evidências esperadas:** `migration list`, catálogo sanitizado, contagens zero, lint, suíte local, registro em `docs/run_log.md`.

**Fora do escopo:** seed remoto, tabela espelho, dados reais, edição da baseline, `migration repair`, `db reset --linked`.

**Checkpoint de 2026-08-06:** estado técnico remoto `baseline_applied_validated`. Uma migration local e remota convergente; cinco tabelas; 27 constraints; 14 índices; RLS habilitado; zero policies; grants esperados; Data API HTTP 200; zero linhas. Nenhuma escrita foi executada. A validação humana formal continua registrada no gate 9.

## Fase 1 — Ingestão Google Sheets

**Objetivo:** autenticar com Service Account, ler uma planilha fictícia, registrar fonte, capturar cabeçalho/dados e respeitar quotas com retries e timeout.

**Entregáveis:** conector Google atrás do contrato existente; configuração sem segredo; política de timeout/retry/backoff+jitter; mapeamento oficial de quotas; telemetria segura; teste de contrato e integração com planilha fictícia.

**Dependências:** OD-01/03/14; Service Account de homologação; planilha fictícia compartilhada; revisão humana de que os dados são fictícios. `google-auth[requests]==2.56.3` foi aprovado e instalado somente no `.venv`.

**Riscos:** quota, permissão excessiva, vazamento e indisponibilidade Google (R-02, R-05, R-15).

**Critérios de entrada:** baseline validada; contrato de fonte definido; credencial fora do Git; limite de chamadas conhecido.

**Critérios de saída:** leitura real comprovada; nenhuma credencial exposta; falhas tratadas; quota documentada; execução repetível.

**Evidências esperadas:** teste real sanitizado, 401/403/404/429/timeout simulados, contagem de chamadas, logs sem payload/segredo.

**Fora do escopo:** dados pessoais, webhooks/quase tempo real antes de decisão, BI e transformação dimensional.

**Checkpoint local de 2026-08-06:** leitor tipado e transporte HTTP GET v4 implementados com escopo único read-only, configuração externa, normalização mínima, backoff+jitter/`Retry-After`, logs allowlist e diagnóstico sanitizado. Quotas oficiais foram documentadas e 29 testes Google offline passaram. A fase permanece aberta: não houve token, chamada real, contagem real nem comprovação da permissão de leitora.

**Checkpoint remoto de 2026-08-06:** configuração e revisão humana passaram; o token permaneceu em memória e o GET de metadados retornou 403 `authorization`, sem retry e sem conteúdo. O teste opt-in reproduziu a falha. A Fase 1 permanece aberta e `ING-03` não foi promovido. Antes de repetir, um responsável deve conferir, sem registrar identificadores, se a Sheets API está habilitada no projeto da credencial, se o compartilhamento corresponde à mesma Service Account e se a fixture configurada é a pretendida. Nenhuma correção de permissão foi executada automaticamente.

## Fase 2 — Raw e sincronização

**Objetivo:** persistir dados brutos, criar snapshots, calcular diferenças, garantir idempotência e preservar o último dado válido.

**Entregáveis:** escrita transacional em `data_sources`, `sync_runs`, `raw_import_rows` e tabela espelho; chave idempotente; tombstones; checkpoint/manifest; recuperação do último snapshot válido.

**Dependências:** Fases 0–1; política inicial de retenção; tabela espelho criada por migration revisada; banco de staging.

**Riscos:** duplicação, perda raw, falha parcial, indisponibilidade e ausência de backup (R-04, R-08, R-09, R-12).

**Critérios de entrada:** fonte fictícia estável, chaves de negócio aprovadas, DDL revisado, plano de rollback.

**Critérios de saída:** primeira carga; segunda sem duplicação; inserção, alteração, exclusão lógica e restauração detectadas; recuperação testada.

**Evidências esperadas:** contagens reconciliadas, consultas sanitizadas, IDs de execução, teste E2E e registro de falha/rollback.

**Fora do escopo:** exclusão física, alteração destrutiva de schema, histórico real do cliente.

## Fase 3 — Qualidade e schema drift

**Objetivo:** validar tipos, tratar colunas novas, detectar remoções/renomeações e isolar falhas por fonte.

**Entregáveis:** contratos versionados; política aditiva; registro de `schema_change_requests`; classificação de erros; teste batch com fontes independentes; runbook de revisão humana.

**Dependências:** Fase 2; regras de negócio do caso fictício; owner para aprovar mudanças.

**Riscos:** drift silencioso, falso rename, tipo inferido incorretamente e bloqueio geral (R-07, R-08).

**Critérios de entrada:** snapshot/raw confiáveis; baseline de schema conhecida; cenários de fixture definidos.

**Critérios de saída:** cenários de drift testados; fonte problemática isolada; outras fontes continuam; alteração estrutural registrada.

**Evidências esperadas:** testes de coluna nova/ausente/rename/tipo; snapshot preservado; pedido de mudança consultável.

**Fora do escopo:** `DROP COLUMN`, rename ou conversão destrutiva automática.

## Fase 4 — Modelagem analítica

**Objetivo:** definir caso de negócio, criar staging, dimensões, fato, métricas e transformações SQL.

**Entregáveis:** ADR do motor/modelo; dicionário de métricas; views/tabelas staging; dimensões e fato; SQL versionado; reconciliação; benchmark.

**Dependências:** Fases 2–3; OD-02/03/07/08; caso de negócio e granularidade aprovados.

**Riscos:** métrica ambígua, crescimento, PII propagada, consulta lenta e lock-in (R-04, R-06, R-13, R-18).

**Critérios de entrada:** dados fictícios reconciliados; grain, chaves e métricas definidos; retenção preliminar.

**Critérios de saída:** Star Schema funcional; consultas analíticas testadas; métricas reconciliadas; desempenho medido.

**Evidências esperadas:** DDL incremental revisado, testes SQL, resultados de reconciliação e tempos com volume declarado.

**Fora do escopo:** modelo genérico para casos não definidos, dados reais e otimização sem métrica.

## Fase 5 — BI e segurança hierárquica

**Objetivo:** conectar BI, criar dashboard, testar filtros e implementar RLS/RBAC necessário.

**Entregáveis:** decisão da ferramenta; conexão de menor privilégio; dashboard fictício; modelo de identidade/escopos; policies; testes positivos/negativos; medição de carregamento.

**Dependências:** Fase 4; OD-04/06; usuários fictícios; decisão de isolamento por projeto versus escopo interno.

**Riscos:** vazamento entre escopos, permissão excessiva, falha/lentidão do dashboard (R-10, R-15).

**Critérios de entrada:** modelo analítico reconciliado; matriz de acesso aprovada; conexão segura disponível.

**Critérios de saída:** dashboard funcional; usuários com escopos diferentes; dados não autorizados bloqueados; tempo registrado.

**Evidências esperadas:** consultas sob perfis distintos, screenshots sem dados reais, teste negativo e benchmark do dashboard.

**Fora do escopo:** publicação externa ou dados reais antes do aceite de segurança/LGPD.

## Fase 6 — Observabilidade e alertas

**Objetivo:** centralizar logs, definir saúde, alertar por e-mail, evitar repetição e avisar recuperação.

**Entregáveis:** eventos/estados persistidos; retenção; regras de severidade; transportador de e-mail; deduplicação; evento de recuperação; painel/runbook operacional.

**Dependências:** Fases 1–5; OD-08/12/13; canal de e-mail de homologação.

**Riscos:** ausência ou tempestade de alertas, PII em logs e falha silenciosa (R-06, R-08, R-17).

**Critérios de entrada:** códigos de erro estáveis; owners e SLA definidos; logs sanitizados.

**Critérios de saída:** falha simulada; alerta recebido; recuperação registrada; dashboard mantém último dado válido.

**Evidências esperadas:** mensagem recebida sanitizada, chave de deduplicação, timeline de health e teste de stale data.

**Fora do escopo:** pager/WhatsApp/Slack sem decisão; payloads brutos em logs.

## Fase 7 — Viabilidade e operação

**Objetivo:** pesquisar limites gratuitos, estimar custos, avaliar pay-as-you-go, definir onboarding/backfill, planos B/C, retenção e LGPD.

**Entregáveis:** tabela datada de custos/free tiers; cenários; budgets; checklist de onboarding; runbook histórico; matriz B/C; políticas de retenção, minimização, anonimização, backup e descarte.

**Dependências:** OD-01 a OD-15; arquitetura testada; documentação oficial vigente; revisão jurídica/segurança quando aplicável.

**Riscos:** mudança do free tier, custo descontrolado, erro de onboarding, PII e lock-in (R-01, R-03, R-06, R-09, R-16, R-18).

**Critérios de entrada:** ferramentas candidatas e volumes conhecidos; responsáveis disponíveis.

**Critérios de saída:** tabela de custos; limites citados; procedimento de onboarding; contingência; alternativas documentadas.

**Evidências esperadas:** links oficiais e data de consulta, planilha de premissas, ensaio fictício de onboarding/backfill e aprovação humana.

**Fora do escopo:** contratação, gasto, aconselhamento jurídico definitivo ou migração real.

## Fase 8 — Fluxograma e apresentação

**Objetivo:** produzir Draw.io com todas as camadas, ferramenta/risco/limite por etapa e material para a Diretoria de Operações.

**Entregáveis:** fonte `.drawio`; PDF ou PNG; legenda; vínculo a requisitos/ADRs; roteiro executivo; checklist de correspondência arquitetura-diagrama.

**Dependências:** evidências das Fases 1–7; decisões de ferramentas; validação técnica interna.

**Riscos:** diagrama desatualizado, excesso de detalhe, omissão de segurança/quota e conhecimento concentrado (R-01, R-02, R-05, R-11).

**Critérios de entrada:** arquitetura-alvo testada e riscos/custos atualizados.

**Critérios de saída:** `.drawio`; PDF/PNG; correspondência com arquitetura implementada; validação técnica interna.

**Evidências esperadas:** checklist por camada, revisão assinada/registrada e links estáveis para documentos técnicos.

**Fora do escopo:** afirmar produção, escala ou custo que não tenham sido comprovados.

## Critério global de encerramento

Uma fase somente muda para concluída quando requisito, implementação, testes, resultado, riscos, documentação, aceite e pendências estão rastreados. A aprovação humana é obrigatória para SQL aplicável, segurança, custo, LGPD, ferramenta e passagem de fase.
