# Seguranca

`.env` e dados de `data/` sao ignorados pelo Git. Use apenas `.env.example` como referencia e jamais inclua tokens, senhas, URLs privadas ou dados pessoais em artefatos versionados. A varredura de artefatos bloqueia padroes comuns de segredo.

O `service_role` pertence exclusivamente ao backend e nunca ao cliente. Cada instituicao usa credenciais de backend separadas para seu proprio projeto Supabase; nao existe multitenancy no banco. RLS esta habilitado nas tabelas, sem policies permissivas nesta fase. O aplicador exige `apply-local`, URL explicita e `psql`; aceita somente loopback, salvo host de desenvolvimento explicitamente permitido. A URL nunca e registrada. Nao ha `DROP TABLE`, `DELETE` fisico, `DROP COLUMN`, renomeacao, relacionamento entre tabelas espelho ou conversao destrutiva automatica: todos viram pendencias humanas.

## Google Sheets na Fase 1

- A Service Account usa somente `spreadsheets.readonly`; a planilha privada deve ser compartilhada apenas como leitora.
- O JSON da credencial permanece fora do repositório e do Git. A chave é lida somente pelo `google-auth`, e o token existe somente em memória.
- O diagnóstico exige confirmação humana de dados fictícios e rejeita padrões óbvios de dado pessoal sem exibir células.
- Logs contêm somente categoria, tentativa, duração e contagens; título, cabeçalho, células, URL, token, e-mail e ID completo não são registrados.
- Revogação: remover imediatamente o compartilhamento da planilha, desabilitar/rotacionar a chave no projeto Google autorizado e invalidar a cópia local; registrar o incidente de forma sanitizada.
- Produção exigirá classificação de PII, minimização e, quando decidido, anonimização antes da camada analítica. A PoC não autoriza dados reais.
- Em 2026-08-06, a primeira tentativa GET falhou com `authorization`; após habilitar a API e corrigir a aba, a leitura real passou sem expor token, e-mail, URL, ID ou célula. O diagnóstico nunca amplia permissões.

A baseline ativa revoga acesso das funcoes `anon` e `authenticated` as tabelas operacionais e concede acesso ao backend privilegiado. Isso nao substitui a revisao de grants e policies antes de qualquer exposicao ao frontend. `raw_import_rows` pode conter dados pessoais brutos; politica de retencao, minimizacao e descarte ainda precisa ser definida antes do piloto.

Na Fase 2A, payload raw permanece somente em memória no dry-run. Hashes de chave e conteúdo não são logados integralmente e não substituem proteção de PII. Nenhuma escrita raw é permitida até que retenção, minimização e a migration incremental de estado/tombstone sejam revisadas.

As migrations da PoC que continham remocao de estruturas existem somente como arquivos historicos `.sql.txt` e nao sao executaveis pelo Supabase CLI. A baseline aplicada nao contem operacoes destrutivas. Em 2026-08-05, somente essa baseline foi aplicada ao staging, sem seed ou dados. Em 2026-08-06, consultas `SELECT` ao catalogo confirmaram RLS nas cinco tabelas, zero policies, ausencia de acesso de `anon` e `authenticated`, grants esperados ao backend e zero linhas. Isso valida a fundacao fechada, mas nao implementa o RLS/RBAC hierarquico exigido para usuarios da futura camada analitica.
