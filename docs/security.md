# Seguranca

`.env` e dados de `data/` sao ignorados pelo Git. Use apenas `.env.example` como referencia e jamais inclua tokens, senhas, URLs privadas ou dados pessoais em artefatos versionados. A varredura de artefatos bloqueia padroes comuns de segredo.

O `service_role` pertence exclusivamente ao backend e nunca ao cliente. Cada instituicao usa credenciais de backend separadas para seu proprio projeto Supabase; nao existe multitenancy no banco. RLS esta habilitado nas tabelas, sem policies permissivas nesta fase. O aplicador exige `apply-local`, URL explicita e `psql`; aceita somente loopback, salvo host de desenvolvimento explicitamente permitido. A URL nunca e registrada. Nao ha `DROP TABLE`, `DELETE` fisico, `DROP COLUMN`, renomeacao, relacionamento entre tabelas espelho ou conversao destrutiva automatica: todos viram pendencias humanas.

A baseline ativa revoga acesso das funcoes `anon` e `authenticated` as tabelas operacionais e concede acesso ao backend privilegiado. Isso nao substitui a revisao de grants e policies antes de qualquer exposicao ao frontend. `raw_import_rows` pode conter dados pessoais brutos; politica de retencao, minimizacao e descarte ainda precisa ser definida antes do piloto.

As migrations da PoC que continham remocao de estruturas existem somente como arquivos historicos `.sql.txt` e nao sao executaveis pelo Supabase CLI. A baseline aplicada nao contem operacoes destrutivas. Em 2026-08-05, somente essa baseline foi aplicada ao staging, sem seed ou dados. O DDL habilitou RLS, revogou acesso de `anon` e `authenticated` e concedeu acesso ao backend privilegiado; uma verificacao independente desses grants no catalogo permanece pendente pela ausencia local de `psql` ou driver PostgreSQL.
