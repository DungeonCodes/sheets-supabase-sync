# Seguranca

`.env` e dados operacionais de `data/` são ignorados pelo Git; somente fixtures fictícias em `data/fixtures/` são versionadas. Use apenas `.env.example` como referência e jamais inclua tokens, senhas, URLs privadas ou dados pessoais em artefatos versionados. A varredura de artefatos bloqueia padrões comuns de segredo.

Metadados locais gerados pelo Supabase CLI em `supabase/.temp/` e `supabase/.branches/` também são ignorados. Metadados não autenticáveis de staging existem apenas em commits históricos anteriores; o saneamento de histórico foi deliberadamente adiado e não autoriza novo versionamento.

O `service_role` pertence exclusivamente ao backend e nunca ao cliente. Cada instituição usa credenciais de backend separadas para seu próprio projeto Supabase; não existe multitenancy no banco. RLS está habilitado nas tabelas, sem policies permissivas nesta fase. O adaptador transacional recebe uma conexão `psycopg` injetada; no staging autorizado ela usa Session Pooler, e a URL nunca é registrada. Não há `DROP TABLE`, `DELETE` físico, `DROP COLUMN`, renomeação, relacionamento entre tabelas espelho ou conversão destrutiva automática: todos viram pendências humanas.

## Google Sheets na Fase 1

- A Service Account usa somente `spreadsheets.readonly`; a planilha privada deve ser compartilhada apenas como leitora.
- O JSON da credencial permanece fora do repositório e do Git. A chave é lida somente pelo `google-auth`, e o token existe somente em memória.
- O diagnóstico exige confirmação humana de dados fictícios e rejeita padrões óbvios de dado pessoal sem exibir células.
- Logs contêm somente categoria, tentativa, duração e contagens; título, cabeçalho, células, URL, token, e-mail e ID completo não são registrados.
- Revogação: remover imediatamente o compartilhamento da planilha, desabilitar/rotacionar a chave no projeto Google autorizado e invalidar a cópia local; registrar o incidente de forma sanitizada.
- Produção exigirá classificação de PII, minimização e, quando decidido, anonimização antes da camada analítica. A PoC não autoriza dados reais.
- Em 2026-08-06, a primeira tentativa GET falhou com `authorization`; após habilitar a API e corrigir a aba, a leitura real passou sem expor token, e-mail, URL, ID ou célula. O diagnóstico nunca amplia permissões.

A baseline ativa revoga acesso das funcoes `anon` e `authenticated` as tabelas operacionais e concede acesso ao backend privilegiado. Isso nao substitui a revisao de grants e policies antes de qualquer exposicao ao frontend. `raw_import_rows` pode conter dados pessoais brutos; politica de retencao, minimizacao e descarte ainda precisa ser definida antes do piloto.

No dry-run, payload raw permanece somente em memória. Nos gates integrados autorizados, apenas a fixture fictícia foi persistida no staging. Hashes de chave e conteúdo não são logados integralmente e não substituem proteção de PII. Retenção, minimização e LGPD continuam pendências antes de qualquer uso com dados reais.

## Estado raw atual e LGPD

A migration incremental `20260806120000_add_raw_current_state.sql` foi criada, validada localmente e
aplicada ao staging em 2026-08-11. Ela repete o padrão de segurança da baseline: RLS habilitado, nenhuma policy,
`anon` e `authenticated` sem qualquer grant e acesso restrito ao backend. O `service_role` recebe
`select, insert, update` e **não** recebe `delete`, porque a exclusão nesta camada é sempre lógica;
remoção física exige procedimento revisado por humano. Nenhum payload raw é exposto ao frontend e
o RLS/RBAC hierárquico para dashboards continua fora desta fase.

Follow-up de 2026-08-11: os default privileges locais do Supabase inicialmente concederam
privilégios amplos a service_role. A migration incremental foi corrigida para revogar todos os
privilégios em `raw_current_rows` de PUBLIC e das três roles antes do grant mínimo. Após reset
local, testes reais confirmaram SELECT/INSERT/UPDATE permitidos somente para service_role e
DELETE/TRUNCATE/REFERENCES/TRIGGER/MAINTAIN negados; anon e authenticated seguem sem acesso.

Em 2026-08-11, a migration corrigida foi aplicada ao staging. Consulta remota somente leitura
confirmou os mesmos grants mínimos, RLS habilitado e zero policies em `raw_current_rows`; nenhuma
linha foi inserida. Isso não substitui as pendências de retenção, LGPD e RBAC hierárquico.

A terceira migration event-only, aplicada ao staging em 2026-08-11, reduz `raw_import_rows` a SELECT/INSERT para
service_role e mantém anon/authenticated sem acesso e RLS sem policies. Tombstones não duplicam
payload nem content hash. A conexão PostgreSQL é injetada e não aparece nos logs; eventos registram
somente contagens/categorias sanitizadas.

Análise de tratamento de dados, atualizada nesta etapa:

- **PII em payload:** `raw_current_rows.payload_json` e `raw_import_rows.payload_json` guardam a
  linha bruta. Em produção isso pode conter dados pessoais. A fixture persistida nos gates atuais é exclusivamente fictícia.
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

## Retry e resultado desconhecido

PostgreSQL usa SQLSTATE/tipo e estágio, não texto livre. Autenticação, autorização, configuração,
schema, validação e dados inválidos não são repetidos. Conexão perdida durante `COMMIT` é
`ambiguous_outcome`: não há rollback presumido nem retry cego. Logs usam allowlist e nunca incluem
payload, células, senha, URL completa, token, Service Account ou Project Ref completo.
Em 2026-08-11, a terceira migration event-only foi aplicada isoladamente ao
staging. Introspecao somente-leitura confirmou que `raw_import_rows` manteve
RLS sem policies e grants minimos (service_role somente SELECT/INSERT), sem
ampliar acesso de anon ou authenticated. `raw_current_rows` manteve
SELECT/INSERT/UPDATE para service_role e negacao dos privilegios elevados.
Nenhum dado foi inserido e nenhuma integracao Google foi executada.
