# sheets-supabase-sync

Sincronizador auditavel para levar respostas de Google Forms/Google Sheets ao Supabase sem perder os dados brutos. Cada instituicao usa um projeto Supabase exclusivo; cada planilha+aba configurada alimenta uma tabela espelho independente. Esta Fase 1 opera offline com CSVs de fixture; a integracao com a API Google ainda nao foi implementada.

## Arquitetura

```text
Instituicao -> Projeto Supabase exclusivo
Google Sheet + aba -> data_source -> tabela espelho propria
                                 -> sync_runs/raw_import_rows/import_errors/schema_change_requests
```

Nao ha `organization_id`, `tenant_id` ou relacionamentos automaticos entre tabelas espelho.

## Pre-requisitos

- Python 3.12 ou superior;
- opcionalmente Docker e Supabase CLI para a validacao de integracao local.

## Instalacao e uso local

Nao ha dependencias de terceiros na Fase 1. No PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m sheets_supabase_sync.cli --config configs/examples/local.json --input data/fixtures/contacts.csv
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
- baseline institucional consolidada e validada em dry-run, ainda nao aplicada;
- integracao PostgreSQL/Supabase local pendente;
- Google Sheets real pendente;
- agendamento de producao pendente.

As tres migrations da PoC, nunca aplicadas, foram preservadas em
[`docs/history/initial-migrations-poc/`](docs/history/initial-migrations-poc/README.md).
A unica migration ativa aguarda revisao humana antes do primeiro deploy. Depois de aplicada,
ela nao devera ser reescrita: mudancas futuras deverao ser migrations incrementais.

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
```

O comando retorna 0 para saudavel, 1 para aviso e 2 para falha, sem exibir credenciais. Consulte [docs/testing.md](docs/testing.md), [docs/monitoring.md](docs/monitoring.md) e [docs/runbook.md](docs/runbook.md).

## Limitacoes

Concluido: normalizacao, hash deterministico, snapshot, diff, artefatos, varredura antissegredo, baseline SQL e testes offline. A baseline habilita RLS nas tabelas operacionais, revoga acesso de `anon` e `authenticated` e reserva escrita ao backend privilegiado. Ela foi inspecionada com lint e `supabase db push --dry-run`, mas nenhuma migration foi aplicada. Permanecem pendentes a validacao do executor contra PostgreSQL/Supabase local, a API real do Google Sheets e a criacao das tabelas espelho por uma sincronizacao real.

Consulte [docs/architecture.md](docs/architecture.md), [docs/workflow.md](docs/workflow.md), [docs/security.md](docs/security.md) e [docs/roadmap.md](docs/roadmap.md).
