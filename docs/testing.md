# Testes

Os testes rapidos usam somente Python e fixtures deterministicas:

```powershell
$env:PYTHONPATH = "$PWD\src"
py -3.13 -m unittest discover -s tests -v
```

Categorias: `unit` cobre dominio, hashes, erros, retries, alertas e doctor; `contract` valida uma fonte sem depender do conector Google; `security` protege fronteiras; `integration` e `end_to_end` dependem de Supabase local; `performance` e opt-in.

Para o baseline de 10.000 linhas:

```powershell
$env:RUN_SLOW_TESTS = '1'
py -3.13 -m unittest tests.performance.test_small_baseline -v
```

Integracao requer Docker, Supabase local e `psql`; quando ausentes, os testes sao pulados com mensagem explicita. Google real continua futuro e deve usar planilha de homologacao sem dados pessoais.

## Baseline de migrations

`tests/unit/test_migration_baseline.py` verifica que existe exatamente uma migration ativa, que o historico da PoC e inerte, que nao ha SQL destrutivo ou campos multitenant e que seed, constraints, RLS e grants permanecem coerentes.

Fotografia de 2026-08-05: `py -3.13 -m unittest discover -s tests -q` executou 63 testes, com 59 aprovados, 4 pulados por falta dos pre-requisitos locais de integracao e nenhuma falha. O numero nao e uma meta fixa; obtenha o estado atual executando o comando acima.

Os testes de regressao verificam `previous_schema jsonb`, preservacao de `proposed_schema`, ausencia executavel de `current_schema` e rejeicao centralizada de identificadores SQL especiais. O `supabase db push --dry-run` listou somente a baseline corrigida. Dry-run nao comprova execucao do DDL nem substitui testes em PostgreSQL real.

Em 2026-08-05, a baseline corrigida foi aplicada ao staging. `migration list`, lint, estatisticas de tabelas/indices e o schema exposto pela Data API foram verificados somente por leitura. As cinco tabelas apresentaram zero linhas. `psql` e `psycopg` nao estavam disponiveis, portanto consultas diretas ao catalogo e os testes de integracao PostgreSQL permaneceram pendentes.
