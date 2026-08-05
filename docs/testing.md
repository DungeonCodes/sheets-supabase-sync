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

Fotografia de 2026-08-04: `py -3.13 -m unittest discover -s tests -q` executou 62 testes, com 58 aprovados, 4 pulados por falta dos pre-requisitos locais de integracao e nenhuma falha. O numero nao e uma meta fixa; obtenha o estado atual executando o comando acima.

O `supabase db push --dry-run` listou somente a baseline consolidada. Dry-run nao comprova execucao do DDL nem substitui testes em PostgreSQL real.
