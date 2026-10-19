# Probe transacional isolado — execução registrada

> **19/10/2026: GREEN somente para propriedades transacionais testadas.**
> Execução concluída; control.enabled=false, evidência preservada em
> [execution_20261019_sanitized.json](execution_20261019_sanitized.json) e
> [run_log](../../../docs/run_log.md). Não executar novamente: schema já existe.
> O pacote Cron/Edge continua YELLOW. O runbook original segue abaixo como
> registro do procedimento, sem nova autorização de execução.
>
> Exceção humana específica deste teste: leitura dos estados inteiramente
> sintéticos por supabase_read_only_user e supabase_etl_admin foi aceita,
> incluindo seus privilégios pg_read_all_data/BYPASSRLS. Sem EXECUTE/UPDATE
> para esses papéis. postgres e superusuário Supabase permanecem confiáveis.
> Esta exceção não autoriza exposição de qualquer segredo ou dado operacional.

Preparado exclusivamente para **APROVAR PROBE TRANSACIONAL ISOLADO EM STAGING**.
Não executar com a autorização deste gate de revisão. Nenhum arquivo operacional
de `../sql/` faz parte desta aprovação. Não instalar extensão alguma.

## Escopo e pré-condições humanas

Usar três conexões PostgreSQL independentes A/B/C, pelo caminho staging já
autorizado e validado pelo staging guard existente. Não mudar TLS, credenciais
ou conexão. Confirmar identidade staging e current_user=postgres antes de DDL.
Não registrar DSN, variáveis de ambiente ou erros brutos de conexão. Não passar
senha em argumentos/histórico. Um latch de sessão não comprova identidade staging.

Exemplo de comandos **dentro de sessões psql já conectadas com segurança**, a
partir da raiz do repositório. Não abrir conexões novas por tentativa automática.
Em cada sessão, após aprovação e guard:

```sql
\set ON_ERROR_STOP on
SET app.cron_probe_review='isolated-staging-reviewed';
SET lock_timeout='30s';
SET statement_timeout='40s';
SET idle_in_transaction_session_timeout='90s';
SELECT current_user,pg_backend_pid();
```

Os três PIDs devem ser distintos (usar conexões persistentes, não transaction
pooling). A/B não podem usar a mesma conexão. C usa nova transação READ COMMITTED
em cada observação; não reutilizar snapshot REPEATABLE READ. Não usar SQL Editor
para simular sessões persistentes sem comprovar esse comportamento do cliente.

## Objetos e efeitos

`00_setup.draft.sql`: cria schema privado **novo** `cron_tx_probe`, tabelas
`control` (uma linha) e `permits` (três casos sintéticos), funções invoker
`claim(text)` / `no_rearm()` e trigger. PK/checks e row lock; nenhuma função
SECURITY DEFINER, papel/credencial, endpoint RPC público, HTTP ou COMMIT interno.
Owner postgres; search_path=pg_catalog; referências qualificadas. Sem grants
para PUBLIC/anon/authenticated/service_role. Administradores/membros do owner
permanecem confiáveis. `service_role` BYPASSRLS não substitui privilégios SQL.

Setup falha se o schema já existir: nunca apagar/resetar evidência para repetir.
Janela máxima deste probe: 30 minutos após setup. São apenas quatro linhas
isoladas e duas claims confirmadas; nenhuma tabela do sincronizador é consultada
ou modificada. Sem dependência em Vault, pg_cron, pg_net, http, Google ou GitHub.

## Sequência manual, sem executor automático

Parar em qualquer resultado inesperado; ROLLBACK nas sessões abertas e executar
somente a desativação revisada após liberar locks. Não reenviar operações para
resolver resultado desconhecido. Não executar todos os blocos em uma sessão.

1. A, fora de transação: `\i drafts/cron_controlled_dispatch/probe/00_setup.draft.sql`.
   C: `\i drafts/cron_controlled_dispatch/probe/10_observe_readonly.sql`.
   Conferir três contadores zero. Auditar matriz completa de LOGIN e papéis
   cliente: parar se acesso não administrativo ao schema/tabelas/função aparecer.
   A janela/ACL deste probe não autoriza alterar permissões globais.
2. A executa e **mantém transação aberta**:

   ```sql
   BEGIN;
   SELECT cron_tx_probe.claim('rollback') AS won; -- true
   ```

3. C roda `10_observe_readonly.sql`: rollback=0. Isso comprova invisibilidade do
   consumo não confirmado por outro backend. A: `ROLLBACK;`. C observa rollback=0.
4. B confirma o mesmo caso que foi desfeito, numa transação explícita:

   ```sql
   BEGIN;
   SELECT cron_tx_probe.claim('rollback') AS won; -- true
   COMMIT;
   ```

5. C observa rollback=1 e claimed_by_other_backend=true. A simula resposta
   perdida após commit sem rede: não possui o resultado de B; tenta consumir
   novamente, sem qualquer envio externo:

   ```sql
   BEGIN;
   SELECT cron_tx_probe.claim('rollback') AS replay; -- false
   COMMIT;
   ```

6. A inicia corrida e **mantém transação aberta**:

   ```sql
   BEGIN;
   SELECT cron_tx_probe.claim('race') AS won; -- true
   ```

7. B inicia disputa e deixa a consulta bloqueada no lock de A:

   ```sql
   BEGIN;
   SELECT cron_tx_probe.claim('race') AS competing_won; -- aguarda; depois false
   ```

8. Enquanto B aguarda, C observa race=0. Em C, usar os PIDs conferidos de A/B
   como variáveis psql não sensíveis e comprovar o bloqueio, sem ler queries:

   ```sql
   -- Preencher a_pid/b_pid com os números observados, nunca valores de conexão.
   SELECT :a_pid::integer=ANY(pg_blocking_pids(:b_pid::integer)) AS b_waits_for_a;
   ```

   b_waits_for_a deve ser true. Em menos de 30s após iniciar B,
   A executa `COMMIT;`. B retorna **false**, então B executa `COMMIT;`.
   Timeout não é sucesso: registrar inconclusivo e parar, sem resetar casos.
9. C observa race=1, claimed_by_other_backend=true. A confirma replay e expiração:

   ```sql
   BEGIN;
   SELECT cron_tx_probe.claim('race') AS replay; -- false
   SELECT cron_tx_probe.claim('expired') AS expired; -- false
   SELECT cron_tx_probe.claim('unknown') AS unknown_case; -- false
   COMMIT;
   ```

10. C: `\i drafts/cron_controlled_dispatch/probe/20_verify_readonly.sql`.
    Todos os booleanos devem ser true. Não aceitar só contagens finais: guardar
    sequência sanitizada dos resultados anteriores e três backends distintos.
11. A: `\i drafts/cron_controlled_dispatch/probe/30_disable.draft.sql`.
    Deve retornar disabled=true. B: `BEGIN; SELECT cron_tx_probe.claim('race');
    COMMIT;` deve retornar false. C observa contadores preservados 1/1/0.

## Critérios, rollback e limites

Sucesso: uma vitória confirmada por caso válido, concorrente/replay recusados,
estado não confirmado invisível em C e visível depois, rollback não consumiu,
expirado/ausente recusados, desativação confirmada, zero acesso a negócio/rede HTTP.
Guardar só booleanos, contadores, casos sintéticos e horário; nunca logs de conexão.

Rollback é **lógico**: `30_disable.draft.sql` desabilita control sob lock, preserva
contadores e evidência. Requer mesmo latch/aprovação. Não usa DROP, DELETE,
TRUNCATE, reset de claim ou alteração de grants fora do schema isolado.
Locks/timeout: encerrar transações abertas primeiro; se ainda houver bloqueio,
parar e investigar sessões conhecidas, sem cancelamento genérico de outros jobs.
Remoção física futura do schema exigirá revisão e aprovação específicas.

Não prova PostgREST, estabilidade/durabilidade da plataforma após restore,
ACL de net/Vault, chamada CALL em Cron, Edge, HTTP ou workflow_dispatch. Não há
CALL neste mecanismo e nenhuma ordem interna de comandos finge um COMMIT.
Não é exactly-once. O consumo do probe é um modelo reduzido da barreira proposta;
o caminho de produção corrigido precisará de sua própria prova após revisão.
