# CRON_EDGE_AUTHORIZATION_REDESIGN — YELLOW

**Offline, sem implantação. Decisão humana: exigir prova da origem Cron.**
Os gates remoto e transacional continuam GREEN, sem repetição. Baseline 9/11/8
é contexto do último gate, não uma medição nova. O probe real e sua evidência
permanecem intactos. Este diretório substitui os rascunhos operacionais antigos
como proposta corrente; os oito SQLs legados permanecem históricos e bloqueados.

## Decisão e bloqueio que permanece

Wake-only público com UUID não secreto foi **rejeitado** para iniciar dispatch.
Uma chamada falsa antes da liberação deve ser recusada; depois da liberação,
também não ganha legitimidade só porque o estado do banco permite consumir.
O humano confirmou expressamente que iniciar a operação aprovada dentro da
janela não basta: é necessário comprovar a origem da chamada.

O banco pode comprovar autorização/estado e exclusivo vencedor; não autentica
quem iniciou uma requisição HTTP. No fluxo pg_net, URL/header/body são legíveis
por papéis conectáveis. ID aleatório, header X-Cron, IP de saída compartilhado,
UUID do run, marca de liberação no banco, nonce em plaintext e bearer global
não resolvem essa fronteira. Assinar uma mensagem pode proteger integridade,
mas a cópia da mensagem autenticada ainda pode ganhar uma corrida por replay;
não chamar isso de prova de que o transporte atual veio do Cron legítimo.

Sob a política confirmada, **não há neste pacote uma implementação aprovada
de ingresso Cron autenticado**. Não foi documentada uma identidade nativa de
workload pg_net que satisfaça esse requisito. Não inventar essa capacidade.
É preciso revisar um mecanismo de prova ligado ao emissor/canal, com chave ou
identidade mantida fora da fila e fora das tabelas legíveis pelos leitores
privilegiados, ou rever a fronteira arquitetural. Ex.: avaliar transporte com
autenticação mútua/assinatura não exportável e proteção contra captura/replay,
somente se suportado pelo emissor e pela plataforma; isso **não está disponível
ou provisionado por estes rascunhos**. Um intermediário que só repasse UUID ou
confie em IP não acrescenta a garantia e não será considerado solução.

Consequência deliberada: o wake público retorna 403 sem sequer consultar o
ledger; não consome, não enfileira trabalho, não pode queimar a autorização.
O handler que faz dispatch exige `verifyIngress` independente, antes da claim.
Nenhum verificador real é fornecido. O entrypoint antigo e o novo abortam na
inicialização; não existe listener implantável ou fallback público neste gate.
Isso é um bloqueio de segurança explícito, **não um fluxo completo funcional**.

## Componentes preparados

| Arquivo | Propriedade |
| --- | --- |
| edge/dispatch.mjs | Wake sem capacidade de consumo; handler autenticado com verificador obrigatório injetado, binding repo/workflow/dev/SHA/release/janela; sem bearer compartilhado |
| edge/ledger.mjs | Adapter PostgreSQL com três consultas parametrizadas fixas e conexão/transação nova por operação; nenhuma chave service_role ou cliente HTTP genérico |
| edge/index.ts | Exporta código verificável offline e aborta; identidade de ingresso e driver vivo pendentes |
| sql/10_control.draft.sql | Schema novo cron_dispatch_v2, owner e capacidade Edge NOLOGIN sem superuser/BYPASSRLS, tabela de metadados e invariantes |
| sql/20_routines.draft.sql | Release/cancel só operador; claim/confirm/finish só papel Edge, trigger impede rearme |
| sql/30_audit_readonly.sql | Metadados de ownership/roles/ACL/EXECUTE e schemas expostos; não executado |

Os dois SQLs mutáveis abortam incondicionalmente antes de qualquer DDL.
São instalação nova e falham se nomes já existirem; não usar IF NOT EXISTS
para esconder drift, nem aplicar sobre o schema cron_tx_probe do gate concluído.
Não há script de ativação, novo job, enqueue HTTP ou criação de secrets no v2:
conectar essas peças sem a prova de origem contrariaria a decisão humana.

## Privilégios e fronteira de confiança

Proposta para revisão futura: owner `cron_dispatch_owner_v2` NOLOGIN,
NOSUPERUSER, NOBYPASSRLS e sem CREATEROLE/CREATEDB/REPLICATION. Dono apenas do
schema/controle/funções novos; nenhum acesso especial a tabelas operacionais.
SECURITY DEFINER só para funções pequenas qualificadas, owner restrito,
search_path=pg_catalog. Não é necessário dar à Edge o poder amplo de postgres.

`cron_dispatch_edge_v2` também NOLOGIN/NOBYPASSRLS é uma capacidade, não uma
credencial pronta. Recebe USAGE no schema e EXECUTE **somente** em claim,
confirm, finish. Nenhum INSERT/UPDATE/SELECT de tabela, CREATE, membership do
owner, EXECUTE de release/cancel, listagem de autorizações ou poder de rearme.
Não há RPC em public nem schema novo exposto via Data API. PUBLIC/anon/
authenticated/service_role têm EXECUTE revogado nas funções. DDL/grants são
transacionais para não haver janela de EXECUTE público na criação.

Identidade real de conexão, driver e binding staging ainda exigem revisão:
papel LOGIN dedicado sem privilégios adicionais, com membership apenas da
capacidade Edge, credencial só no secret store Edge e TLS com identidade do
servidor verificada. Não usar SUPABASE_DB_URL padrão de postgres nem fallback
service_role. Não criar papel LOGIN, senha, token ou dependência neste gate.
Auditar memberships efetivos e ACLs antes de qualquer implantação.

Limite conhecido: um LOGIN novo herda grants PUBLIC da plataforma, inclusive
net quando instalado. Reduzir privilégios do ledger não remove isso. Não afirmar
que a credencial SQL inteira só pode executar três operações; avaliar esse
risco e alternativas de mediação antes de aprovar sua emissão. Nenhuma mudança
global de CONNECT, PUBLIC, papéis internos, Vault ou net está proposta/aplicada.

Leitores internos/BYPASSRLS podem ler o ledger; não há garantia de confidencialidade
contra eles. Nunca armazenar PAT, chave privada, DSN, bearer, assinatura de
ingresso, dados pessoais ou corpo HTTP nessa tabela. Metadados de autorização
real também terão sua classificação revisada antes de implantação: a exceção
de leitura do probe sintético não os aprova automaticamente. Supabase_admin e
operadores de deployment continuam administradores confiáveis da plataforma;
este código não oferece isolamento contra eles nem contra código Edge malicioso.

## Protocolo de consumo, sob ingresso futuro comprovado

1. Operador cria uma autorização de metadados com SHA/janela/job fixos, sem Edge
   poder criar/rearmar. Cron wrapper futuro deve verificar job/user/database/
   command reais e desativar o job; não existe tal wrapper v2 aprovado agora.
2. Release por rotina exclusiva do operador, na mesma transação do futuro enqueue.
   Estado `released` só é visível após COMMIT. Isso é pré-condição de autorização,
   não autenticação da chamada HTTP. Falha/rollback impede release persistida.
3. Verificador confiável de ingresso valida origem e operação inteira. Grant
   não vem de header/JSON sem autenticação. TTL máximo cinco minutos; binding
   UUID, release_id, repo, workflow, ref dev, SHA esperado e janela.
4. Edge usa sua identidade SQL restrita. claim trava a linha e revalida relógio,
   estado, release e SHA depois do lock. Expirado, não liberado, desconhecido,
   cancelado ou consumido retorna false sem rearmar.
5. Adapter espera COMMIT da claim. Uma chamada em transação nova READ ONLY
   confirma receipt/estado persistido. Sem pg_xact_status/claim_xid. Se a resposta
   de commit se perder, não envia; consumo pode permanecer e o envio se perder.
6. Um único fetch GitHub, URL/repo/workflow/dev literais. Timeout 15s, redirects
   bloqueados, zero retries. HTTP 200 exige workflow_run_id e URLs oficiais;
   204/timeout/JSON inválido são ambíguos. Não guardar corpos/headers/erros brutos.
7. finish só admite resultado sanitizado e receipt válido de estado consumido.
   Falha de auditoria não reenvia. Reconciliar run existente; HTTP 200 não prova
   dispatcher concluído. Inputs/título UUID+SHA no fragmento de workflow anterior
   continuam necessários; SHA divergente deve parar antes de secrets/Python.

Uma chamada não autenticada não consome. Entre chamadas realmente autenticadas,
há no máximo um vencedor se estado não for restaurado/rearmado por administrador.
Garantia de aplicação: até um fetch por autorização; pode haver zero envio após
falha/expiração depois da claim. Não afirmar exactly-once ou entrega garantida.
DoS de endpoint público/quotas continua possível mesmo sem consumo; nenhuma
arquitetura aqui prova disponibilidade sob ataque. Não implementar retries para
contornar esse limite. Cancelar antes de consumir; nunca desfazer consumo ou
reenviar após resposta ambígua. Não há rollback de um dispatch aceito pelo GitHub.

## PAT e operação

PAT futuro granular, só DungeonCodes/sheets-supabase-sync, Actions:write,
validade limitada, exclusivamente no secret store Edge. Essa permissão também
alcança outros workflows/ações no repositório; não é restrita ao arquivo/ref.
Nem PAT nem credencial DB/ingresso passam por pg_net, SQL, prompts ou logs.
Nenhuma credencial foi criada. Sete GitHub Secrets preservadas. Não modificar
sincronizador, migrations, Analytics, Cron, dependências ou workflows neste gate.

## Testes e evidência

```powershell
node --test tests/cron_dispatch/redesign.test.mjs tests/cron_dispatch/dispatch.test.mjs tests/cron_dispatch/review.test.mjs
.venv/Scripts/python.exe -m unittest discover -s tests/unit -p test_cron_dispatch_drafts.py -v
deno check --no-remote --no-config drafts/cron_controlled_dispatch/redesign/edge/index.ts
```

68 Node aprovados: 33 novos do redesign e 35 anteriores preservados. Oito
contratos Python aprovados; Deno check aprovado. Nenhuma rede de teste, SQL
aplicado ou nova execução dos gates remotos. Mock `verifyIngress` **não comprova
identidade Cron**; modelo ledger não executa PostgreSQL. SQL novo ainda não tem
validação de servidor, ACLs implantadas ou prova de driver real; o probe antigo
comprova apenas suas propriedades específicas, não este protocolo inteiro.

## Próxima aprovação e rollback

**APROVAR REVISÃO DA FRONTEIRA DE INGRESSO COM PROVA DE ORIGEM CRON**.
Revisar mecanismo concreto de identidade fora da fila/ledger antes de emitir
credencial ou remover travas. Não solicitar aprovação de deploy com um verificador
fictício. O próximo gate é essa decisão arquitetural, sem implantação implícita.
Até lá, rollback local é manter ambos entrypoints e DDL bloqueados. Nenhum
rollback operacional é necessário porque nada foi aplicado. Preservar evidências
do probe, não executar de novo, não apagar autorizações nem restaurar grants amplos.

Fontes oficiais consultadas em 19/10/2026:

- [Supabase: visibilidade dos headers pg_net](https://supabase.com/docs/guides/troubleshooting/database-roles-can-read-request-headers-queued-by-pg_net-ad6357)
- [Supabase: limites de REVOKE pg_net](https://supabase.com/docs/guides/troubleshooting/revoking-access-to-pg_net-objects-has-no-effect-0bbc16)
- [Supabase: funções e EXECUTE](https://supabase.com/docs/guides/database/functions)
- [PostgreSQL: segurança de funções](https://www.postgresql.org/docs/current/sql-createfunction.html)
- [Supabase: conexão PostgreSQL em Edge](https://supabase.com/docs/guides/functions/connect-to-postgres)
