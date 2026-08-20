# sheets-supabase-sync

Sincronizador auditável de uma Google Sheet fictícia para o raw operacional de
um projeto Supabase isolado por instituição. A Atividade 3 busca substituir
processos manuais de planilha por uma base ETL segura, rastreável e evolutiva;
ela ainda não inclui a camada analítica, BI ou RBAC hierárquico.

## Arquitetura atual

```text
Google Sheets (somente leitura)
        -> Python
        -> psycopg
        -> Supavisor Session Pooler
        -> PostgreSQL / Supabase staging
```

O domínio calcula o snapshot e o diff por identidade lógica. O adaptador
PostgreSQL protege cada fonte com advisory transaction lock, grava histórico
event-only e mantém o estado atual versionado. Credenciais ficam fora do
repositório; Google usa exclusivamente `spreadsheets.readonly`. Operações
remotas são gates humanos controlados, e RLS/grants permanecem restritivos.

## Estado do projeto

### Validado no staging, somente com fixture fictícia

- leitura real Google Sheets em modo read-only;
- primeira carga, idempotência, update, tombstone, restore e reorder de linhas;
- identidade lógica, versionamento e histórico event-only;
- transação PostgreSQL, advisory xact lock, rollback e Session Pooler;
- migrations 3/3, RLS/grants restritivos e `import_errors=0` nos gates validados;
- schema drift validado: coluna adicionada/removida e rename bloqueados; reorder de headers compatível; header duplicado rejeitado pelo leitor.

### Em andamento

- falhas/retry operacional e observabilidade inicial.

### Pendente

- falhas/retry operacional e observabilidade;
- retenção, minimização e LGPD;
- múltiplas fontes;
- RBAC hierárquico;
- camada analítica e BI.

## Setup local e dry-run seguro

Pré-requisitos: Python 3.13, ambiente virtual, e opcionalmente Docker e
Supabase CLI para integração **local**. Nunca copie credenciais para o projeto.

```powershell
$env:PYTHONPATH = "$PWD\src"
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m sheets_supabase_sync.cli --config configs/examples/local.json --input data/fixtures/contacts.csv
.\scripts\test.ps1
```

O comando CLI acima é um dry-run local: produz artefatos em `runtime/` e não
acessa Google ou Supabase. Veja [.env.example](.env.example) para placeholders
seguros. A conexão PostgreSQL transacional de staging, quando autorizada, usa o
Session Pooler na porta 5432; a URL real continua exclusivamente no ambiente
privado.

## Testes locais

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe scripts\check-docs.py
Remove-Item Env:PYTHONPATH
.\.venv\Scripts\python.exe -m pip check
```

`PYTHONPATH` é necessário somente para executar a suíte diretamente do código-fonte.
Remova-o antes de `pip check`, que valida exclusivamente as distribuições instaladas.

Integrações Google e PostgreSQL são opt-in. Não as habilite sem autorização
específica. Para Supabase local, use `scripts/start-supabase.ps1`,
`scripts/test-integration.ps1` e `scripts/stop-supabase.ps1`; o script de
integração usa a `.venv` e não requer `psql` no host.

## Onde começar a leitura

1. [Índice da documentação](docs/index.md).
2. [Arquitetura](docs/architecture.md) e [roadmap](docs/roadmap.md).
3. ADRs de estado raw, histórico event-only e schema drift em [docs/decisions](docs/decisions/).
4. [Testes](docs/testing.md) e [segurança](docs/security.md).
5. Documentos da [Atividade 3](docs/activity-3/).
6. [Run log](docs/run_log.md), apenas como histórico detalhado.

- dominio e sincronizacao validados offline;
- baseline institucional corrigida, aplicada em 2026-08-05 e validada por inspecao somente de leitura em 2026-08-06;
- integracao PostgreSQL/Supabase local pendente;
- leitor Google Sheets read-only implementado, validado offline e comprovado com 7 colunas/5 linhas fictícias;
- migration incremental de estado raw criada em 2026-08-06, validada offline e nao aplicada;
- agendamento de producao pendente.

As tres migrations da PoC, nunca aplicadas, foram preservadas em
[`docs/history/initial-migrations-poc/`](docs/history/initial-migrations-poc/README.md).
A baseline registrada no staging nao deve mais ser reescrita: mudancas futuras
sao migrations incrementais. Em 2026-08-06 foi criada a primeira delas,
`20260806120000_add_raw_current_state.sql`, que separa historico e estado raw
atual. Ela e aditiva e permanece **nao aplicada** em qualquer ambiente.

A primeira tentativa de aplicacao, em 2026-08-04, falhou com `SQLSTATE 42601`
antes do registro da migration. Em 2026-08-05, a inspecao somente leitura confirmou
rollback completo; o campo conflitante foi renomeado de `current_schema` para
`previous_schema`, e testes, lint e dry-run passaram novamente. A segunda tentativa,
explicitamente autorizada em 2026-08-05, aplicou somente a baseline corrigida. O seed
nao foi executado e nenhuma tabela espelho ou linha de dados foi criada.

Em 2026-08-06, uma reconciliacao independente e somente de leitura confirmou uma
migration local e uma remota na mesma versao, as cinco tabelas operacionais, 27
constraints, 14 indices, RLS habilitado, zero policies, grants restritos ao backend,
Data API acessivel e zero linhas. Nenhum identificador de projeto ou credencial foi
registrado.

## Modos de execucao

- `dry-run` e o padrao: gera artefatos e atualiza o snapshot local, sem conectar ao banco.
- `generate-sql` gera os mesmos artefatos auditaveis, sem aplicar SQL.
- `apply-local` exige `--database-url`, aceita apenas host local por padrao e usa `psql` em transacao unica.

Exemplo de demonstracao local, apos iniciar o Supabase e obter uma URL PostgreSQL local:

```powershell
./scripts/demo-local.ps1 -DatabaseUrl 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
```

O roteiro usa apenas fixtures e demonstra importacao inicial, inclusao, alteracao, remocao logica, restauracao e idempotencia. Nunca use uma URL remota.

## Configuracao e agendamento

Use [institution.example.json](configs/examples/institution.example.json) como configuracao executavel sem credenciais. A versao YAML equivalente e documental; o leitor atual usa JSON e evita adicionar uma dependencia YAML. Cada fonte define `spreadsheet_id`, `sheet_name`, `target_table`, `business_key` e `sync_interval_minutes` (180 minutos no exemplo).

O nucleo lista fontes vencidas e executa cada uma isoladamente; um scheduler de provedor ainda nao foi implantado.

## Diagnostico

```powershell
python -m sheets_supabase_sync.cli doctor
python -m sheets_supabase_sync.cli doctor --format json
py scripts/verify-credentials.py --local-only
.\.venv\Scripts\python.exe scripts\verify-google-sheets.py --confirm-fictitious
```

O diagnóstico Google exige revisão humana prévia de que a fixture é fictícia, usa apenas `spreadsheets.readonly`, não exibe células e não acessa Supabase. Consulte [docs/testing.md](docs/testing.md), [docs/monitoring.md](docs/monitoring.md), [docs/runbook.md](docs/runbook.md) e [limites da API](docs/activity-3/google-sheets-api-limits.md).

## Limitacoes

Concluido: normalizacao, hash deterministico, snapshot, diff, artefatos, varredura antissegredo, baseline SQL, aplicacao no staging, validação independente do catálogo remoto e implementação local do leitor Google read-only com retry seguro. Permanecem pendentes a prova Google real com fixture fictícia, RLS/RBAC hierarquico para a camada analitica e a criacao das tabelas espelho por uma sincronizacao real.

Consulte [docs/architecture.md](docs/architecture.md), [docs/workflow.md](docs/workflow.md), [docs/security.md](docs/security.md) e [docs/roadmap.md](docs/roadmap.md).

## Atividade 3 — sistema ETL para clientes

O [documento oficial](docs/decisions/20260806_inicie_etl_clientes_orientacao.md) passa a ser a principal fonte de requisitos. A auditoria de 2026-08-06 não implementou funcionalidades nem aplicou migrations e produziu:

- [matriz de 40 requisitos](docs/activity-3/requirements-traceability.md);
- [análise de lacunas](docs/activity-3/gap-analysis.md);
- [plano por fases](docs/activity-3/implementation-plan.md);
- [registro de riscos](docs/activity-3/risk-register.md);
- [decisões empresariais pendentes](docs/activity-3/open-decisions.md);
- [checkpoints de validação](docs/activity-3/validation-checkpoints.md).

O estado técnico da baseline no staging foi reconciliado e validado somente por leitura em 2026-08-06. Após habilitação da Sheets API e correção da aba, a leitura real da fixture passou. A Fase 2A concluiu snapshot, diff e dry-run local de 5 linhas sem persistência. A migration incremental que cria o estado raw atual foi projetada, criada e validada offline em 2026-08-06, mas não foi aplicada e não foi executada em PostgreSQL real. A Fase 2B continua bloqueada até revisão humana do DDL e autorização explícita.

## Falhas operacionais e retry

A política separa `retryable`, `non_retryable`, `busy_deferred` e `ambiguous_outcome`. Google repete
somente falhas transitórias suportadas, com limite, backoff, jitter, budget e `Retry-After`.
PostgreSQL repete conexão transitória e conflitos `40001`/`40P01` por nova transação completa. Lock
ocupado não espera nem cria execução. Perda de conexão durante `COMMIT` nunca dispara retry cego.
As migrations históricas da PoC, nunca aplicadas, ficam em
[docs/history/initial-migrations-poc](docs/history/initial-migrations-poc/README.md).
