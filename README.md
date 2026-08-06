# sheets-supabase-sync

Sincronizador auditavel para levar respostas de Google Forms/Google Sheets ao Supabase sem perder os dados brutos. Cada instituicao usa um projeto Supabase exclusivo; cada planilha+aba configurada alimenta uma tabela espelho independente. O leitor Google Sheets somente leitura está implementado, testado offline e comprovado com fixture fictícia real; a persistência ainda não foi iniciada.

## Arquitetura

```text
Instituicao -> Projeto Supabase exclusivo
Google Sheet + aba -> data_source -> tabela espelho propria
                                 -> sync_runs/raw_import_rows/import_errors/schema_change_requests
```

Nao ha `organization_id`, `tenant_id` ou relacionamentos automaticos entre tabelas espelho.

## Pre-requisitos

- Python 3.12 ou superior;
- ambiente virtual local para as dependências Python;
- opcionalmente Docker e Supabase CLI para a validacao de integracao local.

## Instalacao e uso local

No PowerShell, crie o ambiente virtual do projeto e instale as dependências declaradas:

```powershell
$env:PYTHONPATH = "$PWD\src"
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m sheets_supabase_sync.cli --config configs/examples/local.json --input data/fixtures/contacts.csv
./scripts/test.ps1
```

O comando e um dry-run: produz `runtime/artifacts/latest/manifest.json`, `report.md` e `sync.sql`, alem de um snapshot local. Nenhuma conexao externa e realizada.

## Supabase local

```powershell
./scripts/start-supabase.ps1
supabase db reset --workdir $PWD
./scripts/test-integration.ps1
./scripts/stop-supabase.ps1
```

Execute somente com Docker disponivel. O aplicador em Python recusa hosts remotos e permanece desabilitado nesta fase; revise o SQL antes de usa-lo no ambiente local.

`scripts/test-integration.ps1` executa `supabase db reset` exclusivamente no ambiente local deste repositorio e requer `psql` para aplicar e consultar SQL real.

## Status

Status:

- dominio e sincronizacao validados offline;
- baseline institucional corrigida, aplicada em 2026-08-05 e validada por inspecao somente de leitura em 2026-08-06;
- integracao PostgreSQL/Supabase local pendente;
- leitor Google Sheets read-only implementado, validado offline e comprovado com 7 colunas/5 linhas fictícias;
- agendamento de producao pendente.

As tres migrations da PoC, nunca aplicadas, foram preservadas em
[`docs/history/initial-migrations-poc/`](docs/history/initial-migrations-poc/README.md).
A unica migration ativa foi registrada no staging e nao deve mais ser reescrita:
mudancas futuras deverao ser migrations incrementais.

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

O estado técnico da baseline no staging foi reconciliado e validado somente por leitura em 2026-08-06. Após habilitação da Sheets API e correção da aba, a leitura real da fixture passou. A Fase 2A concluiu snapshot, diff e dry-run local de 5 linhas sem persistência. A Fase 2B está bloqueada: a baseline não possui estado raw único por fonte/chave, tombstone nem versionamento; uma migration incremental revisada será necessária antes de qualquer escrita no staging.
