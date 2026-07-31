# sheets-supabase-sync

Sincronizador auditavel para levar respostas de Google Forms/Google Sheets ao Supabase sem perder os dados brutos. Esta Fase 1 opera offline com CSVs de fixture; a integracao com a API Google ainda nao foi implementada.

## Arquitetura

Google Forms -> Google Sheets -> sincronizador Python -> snapshots, diff e SQL auditavel -> Supabase local. O sincronizador preserva JSON bruto, gera upserts idempotentes e trata remocoes como exclusao logica.

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

Status: fundacao tecnica concluida; validacao end-to-end local pendente.

## Modos de execucao

- `dry-run` e o padrao: gera artefatos e atualiza o snapshot local, sem conectar ao banco.
- `generate-sql` gera os mesmos artefatos auditaveis, sem aplicar SQL.
- `apply-local` exige `--database-url`, aceita apenas host local por padrao e usa `psql` em transacao unica.

Exemplo de demonstracao local, apos iniciar o Supabase e obter uma URL PostgreSQL local:

```powershell
./scripts/demo-local.ps1 -DatabaseUrl 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
```

O roteiro usa apenas fixtures e demonstra importacao inicial, inclusao, alteracao, remocao logica, restauracao e idempotencia. Nunca use uma URL remota.

## Limitacoes

Concluido: normalizacao, hash deterministico, snapshot, diff, artefatos, varredura antissegredo, migrations e testes offline. Pendente: validar o executor contra um Supabase local com Docker, API real do Google Sheets e politicas RLS por usuario/organizacao.

Consulte [docs/architecture.md](docs/architecture.md), [docs/workflow.md](docs/workflow.md), [docs/security.md](docs/security.md) e [docs/roadmap.md](docs/roadmap.md).
