# ADR 20260930: disparo manual de staging por GitHub Actions

## Status

Proposta implementada localmente; execução remota ainda não realizada.
Esta decisão substitui a proposta de borda Vercel da ADR 20260911 para o
primeiro disparo remoto manual.

## Decisão

O primeiro mecanismo remoto será um único workflow manual do GitHub Actions,
`staging-sync-dispatch`, que recebe o nome de uma source e chama o entrypoint
oficial Python existente. Ele não contém regras de diff, lifecycle, retry,
reconciliação ou seleção de dados.

O comando executado é:

```text
python -m sheets_supabase_sync.staging_cli \
  --config runtime/staging.config.json \
  --source <source> \
  --mode apply-staging \
  --confirm-staging
```

O workflow usa `workflow_dispatch` exclusivamente. Não há `schedule:` nem job
Supabase Cron neste gate.

## Configuração e secrets

O GitHub Environment `staging` deve conter apenas os seguintes secrets:

- `APP_ENV`, com o valor de staging;
- `SUPABASE_PROJECT_REF`;
- `SUPABASE_ALLOWED_PROJECT_REF`;
- `SUPABASE_URL`;
- `SUPABASE_DB_URL`;
- `GOOGLE_SERVICE_ACCOUNT_JSON`, usado para materializar o arquivo exigido por
  `GOOGLE_SERVICE_ACCOUNT_FILE` fora do repositório;
- `STAGING_SYNC_CONFIG_JSON`, com a configuração multi-source usada pelo
  entrypoint.

O runner cria `.env.local`, a credencial Google e a configuração apenas durante
a execução, com permissões restritas, e remove os arquivos no final. Nenhum
secret, URL privada ou configuração real é versionado no workflow.

## Concorrência e segurança

`concurrency` serializa o pipeline por branch e `cancel-in-progress: false`
preserva uma execução iniciada até seu resultado transacional ser conhecido.
Os advisory locks por source do Python continuam sendo a proteção de segunda
camada. O workflow recebe somente `contents: read`, usa o Environment `staging`
e valida o staging guard antes de chamar o entrypoint. Production segue bloqueada
pelo próprio guard.

## Caminho para Supabase Cron

O desenho futuro é:

```text
Supabase Cron -> HTTP autenticado -> GitHub workflow_dispatch -> Python -> Google Sheets -> Supabase staging
```

O job Cron não é criado neste gate. Para ativá-lo serão necessários: endpoint
da API GitHub para `workflow_dispatch`, owner/repository, arquivo de workflow,
branch, token GitHub de menor privilégio com permissão de disparo e
armazenamento seguro desse token fora do SQL em texto puro.

## Escala e decisão pendente

O alvo é um disparador global, um workflow e um worker Python que busca e
processa fontes elegíveis. Não haverá cron ou workflow por cliente.

`due_sources` já existe como função de domínio e respeita `enabled` e intervalo,
mas é parcial: a configuração carregada pelo staging CLI não contém
`last_sync_at` atualizado e o worker não consulta fontes/agenda no PostgreSQL.
Antes de conectar o Cron, o Python precisa de um dispatcher oficial que carregue
o estado operacional de staging e aplique essa seleção centralmente. Volume,
quantidade de clientes e planilhas permanecem uma decisão de capacidade do Eric.

## Limites

Esta ADR não cria Cron, token, secret, endpoint, migration, DDL, execução remota
ou acesso de produção. Também não altera o core de sincronização, analytics, BI,
Vercel ou scheduler automático.
