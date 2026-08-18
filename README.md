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

As migrations históricas da PoC, nunca aplicadas, ficam em
[docs/history/initial-migrations-poc](docs/history/initial-migrations-poc/README.md).
