# sheets-supabase-sync

Sincronizador auditável de uma Google Sheet fictícia para o raw operacional de
um projeto Supabase isolado por instituição. A Atividade 3 substitui processos
manuais de planilha por uma base ETL segura, rastreável e evolutiva; não inclui
camada analítica, BI ou RBAC hierárquico.

## Arquitetura atual

```text
Google Sheets (somente leitura)
        -> Python
        -> psycopg
        -> Supavisor Session Pooler
        -> PostgreSQL / Supabase staging
```

O domínio calcula snapshot e diff por identidade lógica. O adaptador PostgreSQL
protege cada fonte com advisory transaction lock, mantém histórico event-only e
estado atual versionado. Credenciais ficam fora do repositório; o Google usa
exclusivamente `spreadsheets.readonly`, e RLS/grants permanecem restritivos.

## Estado do projeto

### Validado

- Google Sheets real com fixture fictícia, somente leitura;
- staging PostgreSQL pelo Session Pooler na porta 5432;
- quatro migrations operacionais aplicadas no staging, RLS/grants restritivos e tabelas raw validadas;
- primeira carga e repetição idempotente reais de `forms_demo` no staging;
- update, tombstone, restore e reorder de linhas validados nos gates anteriores;
- identidade lógica, estado raw versionado e histórico event-only;
- schema drift: alteração de colunas bloqueada, reorder de headers compatível e
  header duplicado rejeitado;
- resiliência transacional: advisory lock, busy/deferred, rollback, retry com
  nova transação/releitura/diff e commit ambíguo sem retry cego;
- observabilidade estruturada, sanitização, política de alertas e deduplicação
  local; SMTP opcional testado por mock;
- multi-source e lifecycle validados; dry-run real de staging com 3 linhas inalteradas e zero escrita.

### Pendente

- automação de retenção e operação com dados reais;
- RBAC hierárquico;
- camada analítica e BI.

## Setup local e dry-run seguro

Pré-requisitos: Python 3.13, ambiente virtual e, para integração local,
Docker e Supabase CLI. Nunca copie credenciais para o projeto.

```powershell
$env:PYTHONPATH = "$PWD\src"
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m sheets_supabase_sync.cli --config configs/examples/local.json --input data/fixtures/contacts.csv
.\scripts\test.ps1
```

O comando CLI é um dry-run local: produz artefatos em `runtime/` e não acessa
Google ou Supabase. Veja [.env.example](.env.example) para placeholders
seguros. Em staging autorizado, a conexão transacional usa Session Pooler na
porta 5432; a URL permanece exclusivamente no ambiente privado.

## Operação assistida da v0.1 em staging

Instale as dependências com os três primeiros comandos do setup acima. Para a
operação Google → Supabase, copie `.env.example` para `.env.local` e preencha
`APP_ENV=staging`, os dois project refs iguais ao projeto de staging permitido,
`SUPABASE_URL`, `SUPABASE_DB_URL` (Session Pooler na porta 5432) e
`GOOGLE_SERVICE_ACCOUNT_FILE`. Guarde o JSON da service account fora do
repositório e conceda a ela somente leitura da planilha fictícia. `.env.local`
e `runtime/` são ignorados pelo Git; não registre secrets ou dados reais.

Copie `configs/examples/institution.example.json` para
`runtime/staging.config.json` e configure uma entrada em `sources[]`: `name`,
`spreadsheet_id`, `sheet_name`, `target_table`, `business_key` (nomes de colunas
normalizados), `sync_interval_minutes` e `enabled=true`. Para uma source já
cadastrada, nome, planilha, aba, target e business key devem coincidir com o
registro do staging; divergência gera `source_mismatch` e não altera a source.
`GOOGLE_TEST_*` em `.env.example` serve ao diagnóstico Google, não substitui os
campos da source neste fluxo.

Depois de revisar o destino e a fixture, execute o dry-run read-only:

```powershell
.\.venv\Scripts\python.exe -m sheets_supabase_sync.staging_cli --config runtime/staging.config.json --source pesquisa-satisfacao --mode dry-run
```

No JSON, `snapshot_rows` é o total lido do Google; `counts.new`, `changed`,
`removed` e `restored` são, respectivamente, inserts, updates, tombstones e
restores planejados. `counts.unchanged` não gera evento de mudança.
`persisted_rows=0` e `status=dry_run` indicam que nada foi persistido. Revise o
plano antes da escrita. Para a sync manual autorizada em staging, use:

```powershell
.\.venv\Scripts\python.exe -m sheets_supabase_sync.staging_cli --config runtime/staging.config.json --source pesquisa-satisfacao --mode apply-staging --confirm-staging
```

O guard exige `APP_ENV=staging`, project ref/URLs do mesmo projeto permitido e
confirmação explícita para escrita. Production é recusada. Um sucesso retorna
`status=applied`; `persisted_rows` conta mudanças, enquanto `sync_runs` pode
aumentar mesmo com diff zero. Falhas retornam apenas categoria sanitizada.
Consulte o [runbook](docs/runbook.md) antes de repetir uma falha ambígua.

## Testes

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe scripts\check-docs.py
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pip check
```

As integrações Google e PostgreSQL são opt-in e exigem autorização específica.
Para Supabase local, use `scripts/start-supabase.ps1`,
`scripts/test-integration.ps1` e `scripts/stop-supabase.ps1`; a integração usa
a `.venv` e não requer `psql` no host. Em clones linked, use explicitamente
`supabase migration list --local` para gates estritamente locais.

## Documentação

1. [Índice da documentação](docs/index.md).
2. [Arquitetura](docs/architecture.md), [testes](docs/testing.md) e [segurança](docs/security.md).
3. ADRs em [docs/decisions](docs/decisions/).
4. Documentos da [Atividade 3](docs/activity-3/).
5. [Run log](docs/run_log.md), apenas como histórico detalhado.

As migrations históricas da PoC, nunca aplicadas, ficam em
[docs/history/initial-migrations-poc](docs/history/initial-migrations-poc/README.md).

## Modos de execução

- `dry-run` é o padrão: gera artefatos e atualiza o snapshot local, sem conectar ao banco.
- `generate-sql` gera os mesmos artefatos auditáveis, sem aplicar SQL.
- `apply-local` exige `--database-url`, aceita apenas host local por padrão e usa `psql` em transação única.

Exemplo exclusivamente local:

```powershell
./scripts/demo-local.ps1 -DatabaseUrl 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
```

O roteiro usa somente fixtures e demonstra primeira carga, inclusão, alteração,
remoção lógica, restauração e idempotência. Nunca use uma URL remota em
`apply-local`.

## Configuração

Use [institution.example.json](configs/examples/institution.example.json) como
configuração executável sem credenciais. Cada fonte define `spreadsheet_id`,
`sheet_name`, `target_table`, `business_key` e `sync_interval_minutes`.

O exemplo [multi-source.example.json](configs/examples/multi-source.example.json)
declara duas fontes ficticias no mesmo projeto institucional. Cada par
planilha/aba e cada mirror devem ser unicos; business keys iguais continuam
isoladas por fonte.

O núcleo lista fontes vencidas e executa cada uma isoladamente; um scheduler de
provedor ainda não foi implantado.

## Diagnóstico

```powershell
.\.venv\Scripts\python.exe -m sheets_supabase_sync.cli doctor
.\.venv\Scripts\python.exe -m sheets_supabase_sync.cli doctor --format json
py scripts/verify-credentials.py --local-only
.\.venv\Scripts\python.exe scripts\verify-google-sheets.py --confirm-fictitious
```

O diagnóstico Google exige revisão humana prévia de que a fixture é fictícia,
usa apenas `spreadsheets.readonly`, não exibe células e não acessa Supabase.

## Limitações atuais

Esta entrega é assistida e limitada a staging com fixture fictícia. Automação
de retenção, Migration 5, analytics/BI, RBAC analítico, scheduler, onboarding
self-service e produção ficam para depois. Consulte [docs/roadmap.md](docs/roadmap.md).

## Falhas operacionais e retry

A política separa `retryable`, `non_retryable`, `busy_deferred` e
`ambiguous_outcome`. PostgreSQL repete apenas conexão transitória e conflitos
`40001`/`40P01`, sempre em nova transação completa. Lock ocupado não espera nem
cria execução; perda de conexão durante `COMMIT` nunca dispara retry cego.

O comportamento de falhas foi validado em PostgreSQL local real. A primeira
carga e a repetição idempotente foram validadas no staging; fault injection
remoto não faz parte desta entrega.
