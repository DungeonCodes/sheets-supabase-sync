# Dashboard local

Aplicação de demonstração em Next.js, TypeScript e Tailwind. A tela inicial usa
somente dados fictícios; não há controles de escrita ou chamadas a staging.

## Instalação e demo

Requer Node.js 20.9+ e npm. Em PowerShell, a partir desta pasta:

```powershell
npm ci
npm run dev
```

Acesse `http://127.0.0.1:3000`. O servidor fica restrito a loopback. O modo demo
não requer autenticação e jamais deve ser usado para dados reais. Para executar
os testes de navegador: `npx playwright install chromium --only-shell` e
`npm run test:e2e`. O teste usa um token exclusivamente sintético.

## PostgreSQL fictício — pendente de revisão humana

O repositório exige revisão humana antes de aplicar qualquer SQL. O candidato
`supabase/migrations/20261111130000_analytics_refresh_candidate.sql`, todas as
migrations anteriores necessárias e o SQL dos testes devem ser revisados antes
de sua execução. Nenhuma migration foi aplicada neste trabalho.

Prepare um servidor PostgreSQL **local**, por exemplo iniciando o Docker Desktop
e um contêiner PostgreSQL dedicado, somente após aprovar a configuração local.
Crie manualmente um banco vazio denominado `analytics_fixture` e os papéis locais
compatíveis com as migrations (`anon`, `authenticated`, `service_role`), seguindo
o SQL revisado. As migrations Supabase existentes também podem depender de
extensões e de outros objetos da instalação local: valide esses pré-requisitos;
não aponte comandos para staging ou produção. Não execute reset de banco existente.

Após a revisão e aprovação explícitas, aplique em ordem as migrations revisadas
somente nesse banco isolado, por um cliente local com privilégios apropriados.
Use uma conexão de loopback numérico com caminho `/analytics_fixture`, sem query
string; `ANALYTICS_FIXTURE_DATABASE_URL` deve ser fornecida pelo operador fora do
repositório. No diretório raiz, habilite `RUN_ANALYTICS_LOCAL_TESTS=1` e execute:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m unittest tests.integration.test_analytics_local tests.integration.test_analytics_pipeline_local
```

O primeiro teste desfaz sua transação; o segundo cria uma source e dados fictícios
persistentes no banco dedicado e imprime sua `source_ref` sintética. Ele usa o
serviço Python real e verifica primeira carga, repetição, mudança, exclusão lógica,
restauração e agregados. Não apaga registros ao terminar. A política de SQL do
repositório também se aplica às instruções SQL dos testes: inclua-as na revisão.

Para abrir essa source no painel, configure no processo local `DASHBOARD_MODE` como
`postgres`, `DASHBOARD_DATABASE_URL` com a conexão somente de leitura ao banco
dedicado, `DASHBOARD_SOURCE_REF` com a referência sintética e
`DASHBOARD_ACCESS_TOKEN` com um valor privado de pelo menos 24 caracteres. O
usuário de autenticação HTTP é `dashboard`; não grave o token no repositório.
O banco precisa conceder ao usuário de leitura acesso mínimo às tabelas consultadas,
incluindo políticas RLS apropriadas aprovadas. A fonte é fixada no servidor: filtros
do navegador não selecionam outras fontes. O painel rejeita hosts não loopback,
outros bancos e parâmetros de conexão em query string.

Com essas variáveis e `RUN_ANALYTICS_LOCAL_TESTS=1`, rode em `apps/dashboard`:
`npx playwright test --config playwright.pg.config.ts`. Este teste de banco não foi
executado neste gate. HTTP Basic sobre loopback é apenas um controle de demonstração;
não é autenticação pronta para hospedagem, TLS, RBAC ou múltiplos usuários.

## Limitações

O status de executor em PostgreSQL é mostrado como ausência de evidência, sem inferir
sucesso. O modo demo não representa staging. A transformação analítica candidata
precisa de validação real de transações, RLS e concorrência antes do uso; categorias
são explicitamente permitidas por fonte e nenhum payload individual chega à tela.
Não publicar o dashboard sem revisão de autenticação, permissões e validação separada.

## Validação hospedada futura

Depois da validação local e de aprovação específica: revisar a migration e o plano
de rollback, obter aceite para escopo de dados e categorias, provisionar identidade
e RBAC/RLS adequados, verificar isolamento por fonte e segredos no servidor, e
autorizar separadamente qualquer deployment ou execução em staging. Verificar
primeira carga, idempotência, tombstone, restauração, erro de fonte e reconciliação
com evidências agregadas. O teste local de demo não autoriza executar esses passos.
