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

Follow-up de 2026-08-11: PostgreSQL local executou as duas migrations e validou DDL, constraints,
idempotência, rollback e advisory lock com fixtures descartadas. A suíte offline permaneceu verde
(141/136/0, 5 pulados); os opt-in existentes continuaram pulados pela ausência de `psql` no host.
O gate de segurança reprovou: `service_role` tem DELETE efetivo em `raw_current_rows`; não há
aprovação para staging até uma correção incremental e nova validação local.

No follow-up de 2026-08-11, a própria migration pendente passou a revogar todos os privilégios
preexistentes antes do grant mínimo. Após `supabase db reset` exclusivamente local, o catálogo e
testes com `SET ROLE service_role` confirmaram SELECT/INSERT/UPDATE permitidos e
DELETE/TRUNCATE/REFERENCES/TRIGGER/MAINTAIN negados; a regressão raw, rollback e advisory lock
também passou. A suíte offline permaneceu em 141 testes, 136 aprovados, 5 pulados e zero falhas.

Deploy em 2026-08-11: o staging aplicou somente a migration incremental. Inspeção agregada
read-only confirmou o mesmo catálogo e contratos de grant, sem linhas nas tabelas operacionais;
lint remoto final passou. Nenhum teste de sincronização ou escrita de fixture foi iniciado.

Checkpoint event-only de 2026-08-11: `scripts/test-integration.ps1` passou a usar o driver Python,
sem depender de `psql` no host. Três testes PostgreSQL locais cobrem ciclo completo, quatro pontos
de rollback e concorrência. A suíte offline executou 150 testes (142 aprovados, 8 pulados); o opt-in
PostgreSQL executou 3/3. O dry-run remoto lista somente a terceira migration.

Deploy event-only em 2026-08-11: a terceira migration foi aplicada ao staging. Introspecao
read-only confirmou CHECK, nulabilidade, UNIQUE logica, grants, RLS/policies e tabelas vazias.
Nenhuma integracao Google foi executada.

Gate integrado interrompido em 2026-08-11: a leitura read-only da fixture
fictícia passou (5 linhas, 7 colunas, zero retries), e o dry-run gerou 5 novas
identidades sem persistir. A abertura da conexão PostgreSQL direta ao staging
falhou antes de iniciar transação ou lock. As contagens remotas permaneceram
zero; não houve segunda sincronização. A suíte continuou em 150 testes, 142
aprovados, 8 pulados e zero falhas.

## Checkpoint integrado de staging em 2026-08-13

Com Session Pooler na porta 5432 e `psycopg[binary] 3.3.4`, duas leituras
independentes da fixture exclusivamente fictícia retornaram 5 linhas e 7
colunas, sem retries. A primeira sincronização transacional criou 5 estados e
5 eventos `insert`; a segunda encontrou 5 registros inalterados e não criou
evento. As duas execuções usaram advisory transaction lock e commit. A prova
agregada remota confirmou versões 1, zero tombstones e `import_errors=0`.
Após o gate, a suíte executou 150 testes: 142 aprovados, 8 pulados e zero
falhas; os testes PostgreSQL locais e o teste Google opt-in não foram
habilitados nesta execução de suíte.

## Ciclo de mudanças integrado no staging em 2026-08-17

O staging comprovou update, tombstone, restore e reorder com a fixture fictícia
e leituras Google read-only separadas. Os planos foram, respectivamente, 1
changed, 1 removed, 1 restored e 5 unchanged. O reorder não criou evento nem
incrementou versão. O estado agregado final é 5 estados, 8 eventos (5/1/1/1 por
tipo), 6 runs aplicados e zero erros. Migrations 3/3 e lint permaneceram verdes.

## Checkpoint parcial de schema drift em 2026-08-17

Testes locais cobrem bloqueio de coluna adicionada antes de mutação raw,
deduplicação de request e reorder compatível por mapeamento por nome. No staging,
coluna adicionada, removida e rename foram bloqueados um por vez; nenhuma
mudança criou evento raw, versão nova, tombstone falso ou `sync_run`. A fixture
restaurada retornou a 5 linhas, 7 colunas e dry-run com 5 inalterados.
