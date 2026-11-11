# Dashboard e transformação analítica locais

O executor publicado em dev permanece separado desta implementação. Para a demo,
o dashboard Next.js lê agregados fictícios em memória, sem conexões externas. O
modo PostgreSQL é limitado a loopback numérico, ao banco `analytics_fixture` e a
uma source configurada no servidor; exige autenticação local e retorna agregados.
Esse mecanismo não é RBAC de produção nem autorização para expor o serviço.

A transformação candidata usa o star schema já existente e uma allowlist de
categorias por source. Ela exige transação com snapshot estável, valida a fonte
inteira antes de alterar fatos, preserva identidades e usa tombstones lógicos.
Uma exceção aborta a transação. A migração, grants, RLS, concorrência e evolução
de schema exigem revisão humana e testes num banco local isolado antes de aplicação.

As dependências Next.js, React, PostgreSQL e ferramentas de desenvolvimento foram
explicitamente aprovadas para este trabalho. Dados reais, deploy, SQL remoto e
acesso a produção permanecem fora do escopo. A interface não apresenta payload,
business key ou identificador de registro e não oferece operações de escrita.
