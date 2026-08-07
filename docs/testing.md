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

Checkpoint real de 2026-08-06: após habilitar a Sheets API e corrigir o nome da aba, o diagnóstico e o teste opt-in passaram. Foram lidas 7 colunas e 5 linhas fictícias; nenhum cabeçalho ou valor foi impresso. O 403 da tentativa anterior permanece como histórico; integrações Supabase/`psql` continuam fora desta fase.

Fase 2A acrescenta testes offline para primeira carga, repetição idêntica, inserção, alteração, remoção, restauração, reordenação, chave vazia/duplicada, rollback local, falhas de início/commit/finalização, lock e comandos PostgreSQL parametrizados. O dry-run real lê a fixture e gera plano sem importar ou acessar Supabase.

A migration incremental de estado raw acrescenta testes estruturais e comportamentais offline:
`tests/unit/test_migration_raw_state.py` inspeciona o DDL declarado e
`tests/unit/test_raw_state.py` cobre primeira carga, carga idêntica, alteração, tombstone,
restauração, incremento de versão, reordenação, identidade duplicada, rollback, falha ao registrar
histórico, falha ao atualizar estado, falha ao finalizar execução, lock sem espera, SQL estático
parametrizado e logs sanitizados.

## Baseline de migrations

`tests/unit/test_migration_baseline.py` verifica que a baseline aplicada permanece byte a byte
inalterada (digest SHA-256), que ela é a migration mais antiga, que o historico da PoC e inerte,
que nao ha SQL destrutivo ou campos multitenant e que seed, constraints, RLS e grants permanecem
coerentes.

`tests/unit/test_migration_raw_state.py` exige exatamente uma migration incremental além da
baseline e verifica nome/ordem, ausência de `DROP`, `TRUNCATE`, `DELETE FROM`, `ALTER COLUMN` e
renomeação, existência de `public.raw_current_rows`, unicidade por `(data_source_id, row_key_hash)`,
chaves estrangeiras esperadas, tombstone, versão, checks de consistência, índices previstos, RLS
habilitado, ausência de acesso de `anon`/`authenticated`, grant do backend sem `delete`, ausência de
segredo e ausência de campos multitenant.

Fotografia de 2026-08-05: `py -3.13 -m unittest discover -s tests -q` executou 63 testes, com 59 aprovados, 4 pulados por falta dos pre-requisitos locais de integracao e nenhuma falha. O numero nao e uma meta fixa; obtenha o estado atual executando o comando acima.

Os testes de regressao verificam `previous_schema jsonb`, preservacao de `proposed_schema`, ausencia executavel de `current_schema` e rejeicao centralizada de identificadores SQL especiais. O `supabase db push --dry-run` listou somente a baseline corrigida. Dry-run nao comprova execucao do DDL nem substitui testes em PostgreSQL real.

Checkpoint de 2026-08-06 para a migration incremental: a suíte offline executou 141 testes, com 136
aprovados, 5 pulados por falta de Docker/`psql`/credencial e nenhuma falha. `supabase migration list`
mostrou duas migrations locais e uma remota, sem divergência; `supabase db lint --linked` não
encontrou erro de schema; `supabase db push --dry-run` listou somente
`20260806120000_add_raw_current_state.sql`. **O lint incide sobre o schema remoto, que ainda não
contém a nova migration; ele não valida o DDL incremental.** O DDL incremental **não** foi executado
em PostgreSQL real: Docker e `psql` estão ausentes nesta máquina e nenhuma infraestrutura foi
instalada. O dry-run real da fixture foi repetido após a mudança e retornou 7 colunas, 5 linhas,
5 novas, 5 comandos de inserção de estado e zero persistidas.

Em 2026-08-05, a baseline corrigida foi aplicada ao staging. Em 2026-08-06, `migration list`, `inspect db`, geração de tipos, consultas `SELECT` via Management API e Data API reconciliaram o estado: cinco tabelas vazias, 27 constraints, 14 índices, RLS e grants coerentes. O dump schema-only não rodou sem Docker, mas deixou de ser necessário para o catálogo porque `supabase db query --linked` permitiu as consultas somente de leitura. Os testes de integração local continuam pulados sem Docker e `psql`.
