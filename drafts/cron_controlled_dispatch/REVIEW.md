# CRON_STAGING_INACTIVE_PREPARATION_REVIEW — 19/10/2026

**YELLOW. Arquitetura candidata com correções necessárias; não implantar.**
Atualização 19/10: probe PostgreSQL isolado executado com sucesso sob autorização
específica de leitura privilegiada dos estados sintéticos; desativado ao final,
contadores operacionais 9/11/8 antes e depois. Ver [evidência](probe/execution_20261019_sanitized.json)
e run_log. Isso não aprova identidade Edge, fila, secrets ou Cron; os achados
e bloqueios operacionais desta revisão continuam válidos. As referências abaixo
a probe pendente são o histórico da revisão, anterior à execução autorizada.
Gate `automation_remote_runner_validated` continua GREEN, run 39247320871.
Segurança anterior MITIGATED; sem reabrir tokens revogados. Baseline contextual
9/11/8, não consultado novamente. Nenhuma operação remota neste gate, salvo
leitura de documentação pública. Branch dev, HEAD 7c3649c.

## Auditoria integral dos oito scripts e da Edge

| Artefato | Resultado da revisão |
| --- | --- |
| 00_inspect_readonly | READ ONLY e sanitizado; matriz de apenas quatro papéis é insuficiente. Complemento de metadados em review_role_inventory_readonly.sql; não executado |
| 10_extensions | Instala duas extensões desnecessárias ao primeiro probe. Bloqueado; nenhuma instalação aprovada |
| 20_private_schema_and_acl | Owner postgres, funções qualificadas, contadores/imutabilidade adequados como base. REVOKE net não é garantia suportada em Supabase hospedado; grants pertencem a supabase_admin. Checks finais falhariam, não estabelecem isolamento operacional. Revogações globais de Vault exigem análise de dependências. Bloqueado |
| 30_routines | Lock seguido de rechecagem de expiração e contadores limita winners. RPCs SECURITY DEFINER/search_path fixo não fazem COMMIT. service_role continua amplo fora das RPCs; bearer global reutilizável e superfície pública de RPC precisam redesenho. Probe RPC atual mistura implantação completa e credencial ampla: rejeitado como primeiro probe. Bloqueado |
| 40_configure_inactive | Transação cria/desativa job antes de torná-lo visível; não executá-lo para validar apenas transações. IF NOT EXISTS não valida integralmente drift de objetos existentes nos outros scripts. Bloqueado |
| 50_arm_once | Guarda separada é útil; premissas ACL net e probe RPC são inválidas/incompletas. Não está autorizado; bloqueado |
| 60_validate_readonly | Projeções sanitizadas; ausência de fila não comprova ausência de envio; pg_xact_status não substitui observação independente, pode não servir como histórico permanente. Não rodar sem objetos instalados |
| 70_disable_rollback | Cancela apenas não consumidas e desativa job, preserva histórico. Não desfaz dispatch já enviado. Mantido disponível como rascunho de contingência, sem execução |

Cinco scripts operacionais 10/20/30/40/50 agora abortam incondicionalmente na
primeira guarda, antes de mutações. Não remover essa trava sem revisão futura.
O entrypoint Edge também aborta antes de ler env/servir. Nenhum endpoint foi
implantado. Implementações anteriores seguem visíveis para revisão, sem selo
de aprovação; testes legados não aprovam sua segurança operacional.

`dispatch.mjs`, `rpc.mjs`, `index.ts` e `dispatch.test.mjs` foram lidos completos.
O handler fixa repo/workflow/dev, aceita só UUID no corpo, limita corpo a 1024
bytes e não retorna erros/corpos/credenciais. Há timeout RPC 5s e GitHub 15s,
redirect:error, zero loop de retry; timeout/204/200 inválido deixam ambiguous.
O HTTP 200 só é aceito com ID inteiro seguro e URLs oficiais correspondentes.
SHA esperado é input validado e deve ser comparado pelo fragmento de workflow
ANTES de secrets/Python; o handler não prova que dev ainda aponta ao SHA.
Congelamento da janela e conferência da run continuam indispensáveis.

HMAC do handler compara dois valores de bearer, **não assina o corpo nem cria
uma capability vinculada a autorização**. O token global permite chamar claims
futuras se seus UUIDs forem conhecidos. Consumo DB evita segundo winner sob
premissas corretas, mas o vazamento ainda permite corrida/DoS/envio antecipado.
`service_role` não é limitado às funções por receber apenas EXECUTE nelas:
conserva privilégios globais e BYPASSRLS; no inventário anterior lia Vault.
Esse adapter NÃO está aprovado. Não criar endpoints administrativos públicos.

## Transações: o que a barreira realmente prova

Claim em transação T1: row lock, conferir estado/tempo, consumir e confirmar.
Observador T2 independente só consegue ver o registro consumido depois do
commit de T1; deve conferir identidade, receipt imutável, validade e estado.
Não reaproveitar a mesma transação: ela vê suas próprias escritas não confirmadas.
`synchronous_commit=on` solicita confirmação WAL segundo configuração da
plataforma; não prova disponibilidade após restore, failover ou perda de storage.

`pg_xact_status(claim_xid)='committed'` pode detectar consulta na própria
transação, mas é redundante sob independência comprovada e não é mecanismo de
exclusão. Não torna duas transações atômicas nem substitui locks/imutabilidade;
status antigo pode não estar disponível. Preferir protocolo simples T1/T2 com
visibilidade de estado confirmado. Não alterar silenciosamente o SQL legado:
primeiro executar o probe isolado revisado, depois revisar a implementação real.

O mecanismo C usa SELECT em Cron e transações RPC, não depende de CALL/COMMIT
interno. CALL top-level só permite COMMIT nas condições documentadas de invoker,
sem SET declarativo, sem bloco de exceção abrangente e sem BEGIN externo;
pg_cron no caminho libpq pode enviar esse comando isolado, mas este probe não
executa Cron e não o certifica. Função SECURITY DEFINER não pode fazer COMMIT.

Falhas: antes do commit, não enviar; resposta perdida após commit, aceitar
perda do envio; falha na confirmação, não enviar; timeout/erro/resposta ambígua
após envio, manter consumo e investigar run existente. Nenhum retry automático
de rede/dispatch. Entregas repetidas pg_net não podem gerar novos winners.
Garantia futura pretendida é no máximo um fetch de aplicação por autorização,
com possível zero envio, sob estado não restaurado e administradores confiáveis.
Não exatamente uma entrega nem execução GitHub garantida.

## Segurança pg_net / Vault / papéis

A documentação oficial atual informa que objetos net pertencem a supabase_admin;
postgres pode receber aviso em REVOKE sem remover grants. Mudanças por projeto
nessas ACL/RLS não são suportadas. PUBLIC alcança novos LOGIN; podem ler e
inserir/modificar a fila. anon/authenticated normalmente não têm LOGIN e net não
é exposto na Data API, mas isso não é isolamento contra outros acessos SQL.
Não consultar headers para auditar: usar apenas privilégios efetivos e owners.

Headers, URL e corpo da fila devem ser tratados como legíveis por todo papel
capaz de conectar. Vault protege repouso, não o header descriptografado.
PAT exclusivamente no secret store Edge; não enviá-lo por net. Não pôr chave
service_role na fila. O secret store Edge também exige confiança nos operadores
e demais funções do projeto; não é cofre isolado por endpoint.

Correção proposta, ainda **não implementada nem aprovada**: capability diferente
por autorização, curta validade, vinculada a UUID/repo/workflow/dev/SHA/janela;
validada e consumida atomicamente no servidor, sem poder criar autorizações.
Guardar só hash no controle quando tecnicamente viável; nunca incluir PAT.
Alternativa: assinatura HMAC dessa tupla, chave de assinatura fora da fila,
com consumo persistido obrigatório. Uma capability capturada ainda pode vencer
a corrida da operação já autorizada; não deve habilitar operação futura nem
outro destino. Expiração não impede corrida dentro da janela. Aceitar esse
risco explicitamente ou abandonar pg_net nesse limite de confiança.

Para acesso Edge ao ledger, preferir identidade DB dedicada com direitos apenas
de EXECUTE nas três operações, sem LOGIN amplo adicional quando evitável,
sem grants de tabela/Vault e sem emitir credenciais administrativas. Avaliar
JWT de papel dedicado via PostgREST, incluindo quem pode emiti-lo e schemas
expostos, versus conexão DB dedicada; um novo LOGIN herda acesso PUBLIC de net.
Nenhuma dessas alternativas foi provisionada. Não usar a chave ampla atual
por conveniência. Não aprovar a integração até resolver e testar essa fronteira.

Inventário preparado inclui todos LOGIN, memberships, owner/SECDEF/search_path,
privilégios efetivos e schemas; exposição Data API deve ser comprovada no
Dashboard/API settings pelo operador (GUC ausente não prova schema não exposto).
Não presumir RLS suficiente para serviço BYPASSRLS ou proprietário.

## Probe separado, custo e próximos passos

[Runbook](probe/README.md): três conexões, schema privado novo, duas tabelas,
duas funções invoker, um trigger, quatro linhas sintéticas; zero extensões,
HTTP, Cron, Edge, credenciais ou tabelas do sincronizador. Testa rollback,
visibilidade independente antes/depois, concorrência, expiração e replay.
Observação e rollback lógico preparados; nunca resetar consumo nem apagar dados.
Não comprova PostgREST ou fluxo completo. Resultado de banco ainda PENDENTE.

Não há nova dependência ou serviço pago neste probe. Consumo mínimo de catálogo,
quatro linhas e até três conexões por janela curta; conferir capacidade do Free
sem upgrade e abortar sob contenção. Não é benchmark. Controles não expiram
conexões automaticamente: fechar A/B/C ao terminar, preservar evidências.

Risco MEDIUM para integração ainda bloqueada; probe tem efeitos restritos e
reversão lógica. Próxima aprovação apenas:
**APROVAR PROBE TRANSACIONAL ISOLADO EM STAGING**.
Não inclui instalações, job inativo, deploy Edge, PAT, secrets, dispatch ou Cron.

## Fontes oficiais verificadas neste gate

- [Supabase: REVOKE pg_net sem efeito](https://supabase.com/docs/guides/troubleshooting/revoking-access-to-pg_net-objects-has-no-effect-0bbc16)
- [Supabase: cabeçalhos da fila](https://supabase.com/docs/guides/troubleshooting/database-roles-can-read-request-headers-queued-by-pg_net-ad6357)
- [PostgreSQL: isolamento e visibilidade](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL: transações PL/pgSQL](https://www.postgresql.org/docs/current/plpgsql-transactions.html)
- [GitHub: retorno de workflow dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)

Evidências offline registradas em run_log: 35 Node e oito contratos Python
aprovados; Deno check e verificação documental aprovados. Scan sanitizado de
23 arquivos: zero assinaturas de credenciais após classificar um falso positivo
em nome de teste. Revisão manual encontrou somente mocks artificiais; scanner
por padrões não é prova absoluta de ausência. Nenhum SQL/probe foi executado.
