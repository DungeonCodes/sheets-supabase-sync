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

Integracao Supabase requer Docker, Supabase local e `psql`; quando ausentes, os testes sao pulados com mensagem explicita. O leitor Google possui testes offline com transporte falso para configuração, schema, retry, `Retry-After`, sanitização e preservação de linhas. A prova real usa somente a fixture privada revisada e o comando abaixo; sem configuração ou confirmação humana, ela é pulada, não aprovada.

```powershell
$env:PYTHONPATH="$PWD\src"
.\.venv\Scripts\python.exe scripts\verify-google-sheets.py --confirm-fictitious
```

Fixture esperada: uma aba privada compartilhada apenas como leitora, cabeçalho válido e entre cinco e dez linhas sintéticas. Deve conter código fictício, quantidade numérica, categoria textual, data como texto, coluna opcional, uma célula vazia e uma linha completamente vazia. Não deve conter nomes de pessoas, e-mails, CPF, telefone ou qualquer dado real. O ID e o conteúdo não são registrados.

Para habilitar o teste de integração, além das três configurações locais, o operador deve definir na sessão `RUN_GOOGLE_SHEETS_INTEGRATION=1` e `GOOGLE_TEST_DATA_CONFIRMED_FICTITIOUS=1` após a revisão humana. A ausência desses gates produz skip explícito.

Checkpoint real de 2026-08-06: configuração e confirmação humana estavam presentes, mas tanto o diagnóstico quanto o teste opt-in receberam 403 `authorization` no GET inicial de metadados. Nenhum cabeçalho ou valor foi lido. O teste remoto é considerado reprovado, não pulado; integrações Supabase/`psql` continuam puladas quando seus requisitos locais não existem.

## Baseline de migrations

`tests/unit/test_migration_baseline.py` verifica que existe exatamente uma migration ativa, que o historico da PoC e inerte, que nao ha SQL destrutivo ou campos multitenant e que seed, constraints, RLS e grants permanecem coerentes.

Fotografia de 2026-08-05: `py -3.13 -m unittest discover -s tests -q` executou 63 testes, com 59 aprovados, 4 pulados por falta dos pre-requisitos locais de integracao e nenhuma falha. O numero nao e uma meta fixa; obtenha o estado atual executando o comando acima.

Os testes de regressao verificam `previous_schema jsonb`, preservacao de `proposed_schema`, ausencia executavel de `current_schema` e rejeicao centralizada de identificadores SQL especiais. O `supabase db push --dry-run` listou somente a baseline corrigida. Dry-run nao comprova execucao do DDL nem substitui testes em PostgreSQL real.

Em 2026-08-05, a baseline corrigida foi aplicada ao staging. Em 2026-08-06, `migration list`, `inspect db`, geração de tipos, consultas `SELECT` via Management API e Data API reconciliaram o estado: cinco tabelas vazias, 27 constraints, 14 índices, RLS e grants coerentes. O dump schema-only não rodou sem Docker, mas deixou de ser necessário para o catálogo porque `supabase db query --linked` permitiu as consultas somente de leitura. Os testes de integração local continuam pulados sem Docker e `psql`.
