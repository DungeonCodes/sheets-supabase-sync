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

## Estado raw atual e LGPD

A migration incremental `20260806120000_add_raw_current_state.sql` foi criada, validada localmente e
**não aplicada**. Ela repete o padrão de segurança da baseline: RLS habilitado, nenhuma policy,
`anon` e `authenticated` sem qualquer grant e acesso restrito ao backend. O `service_role` recebe
`select, insert, update` e **não** recebe `delete`, porque a exclusão nesta camada é sempre lógica;
remoção física exige procedimento revisado por humano. Nenhum payload raw é exposto ao frontend e
o RLS/RBAC hierárquico para dashboards continua fora desta fase.

Análise de tratamento de dados, atualizada nesta etapa:

- **PII em payload:** `raw_current_rows.payload_json` e `raw_import_rows.payload_json` guardam a
  linha bruta. Em produção isso pode conter dados pessoais. A fixture atual é fictícia e nenhuma
  linha foi persistida em qualquer ambiente.
- **Retenção do histórico:** `raw_import_rows` cresce por execução e é o candidato natural a poda
  por idade. O limite ainda não foi decidido (R-04, OD em aberto).
- **Retenção de tombstones:** uma linha excluída permanece indefinidamente em `raw_current_rows`
  com o último conteúdo conhecido. Isso é deliberado — sustenta restauração e o último dado válido —
  mas significa que a exclusão na planilha **não** apaga o dado do banco.
- **Exclusão lógica operacional ≠ exclusão LGPD:** `is_deleted` sinaliza que a chave saiu da fonte;
  não é resposta a pedido de titular. A eliminação de dados pessoais exigirá procedimento próprio,
  com base legal, escopo (histórico + estado + snapshots locais + backups) e registro. O
  `raw_current_rows_tombstone_idx` existe em parte para tornar esse inventário consultável.
- **Acesso:** somente o backend da instituição. Não há multitenancy; o isolamento continua sendo o
  projeto Supabase exclusivo.
- **Crescimento de storage:** o estado atual é limitado por chaves distintas; o histórico é
  proporcional a execuções × linhas observadas. Anexar observações `unchanged` a cada execução é a
  principal alavanca de custo e permanece uma decisão aberta.
- **Anonimização:** ainda não implementada. Será necessária antes de qualquer camada analítica com
  dados reais.

Nada disso declara a LGPD atendida. Base legal, política de retenção, minimização, anonimização e
procedimento de descarte continuam pendências abertas (R-06, `DQ-03`, `OBJ-03`).

As migrations da PoC que continham remocao de estruturas existem somente como arquivos historicos `.sql.txt` e nao sao executaveis pelo Supabase CLI. A baseline aplicada nao contem operacoes destrutivas. Em 2026-08-05, somente essa baseline foi aplicada ao staging, sem seed ou dados. Em 2026-08-06, consultas `SELECT` ao catalogo confirmaram RLS nas cinco tabelas, zero policies, ausencia de acesso de `anon` e `authenticated`, grants esperados ao backend e zero linhas. Isso valida a fundacao fechada, mas nao implementa o RLS/RBAC hierarquico exigido para usuarios da futura camada analitica.
