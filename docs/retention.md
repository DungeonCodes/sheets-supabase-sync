# Retenção, minimização e LGPD

Esta é uma política técnica recomendada, não uma interpretação de prazo legal.
Prazos legais, titulares, responsáveis e holds devem ser aprovados por humano
antes de qualquer purge.

## Inventário e classificação

| Item | Finalidade | Classe | PII potencial | Retenção recomendada |
| --- | --- | --- | --- | --- |
| `data_sources` | contrato e agenda da fonte | confidential | identificador/URL | enquanto a fonte estiver ativa + 90 dias de offboarding |
| `sync_runs` | auditoria operacional agregada | internal | resumo de erro | 180 dias |
| `raw_current_rows` | estado atual para sync/diff | potentially_personal | `payload_json` | enquanto fonte ativa; remover no offboarding aprovado |
| `raw_import_rows` | histórico event-only/reconciliação | potentially_personal | `payload_json` | 180 dias, sujeito a hold aprovado |
| `import_errors` | erro por linha | potentially_personal | mensagem/payload | 30 dias; payload deve ser evitado pelo produtor |
| `schema_change_requests` | auditoria de contrato | internal | nomes de colunas | 365 dias |
| snapshots e artefatos locais | dry-run e diagnóstico | potentially_personal | registros normalizados/SQL | 7 dias local; apagar no offboarding |
| logs/eventos/alertas | operação | internal | referência segura | 30 dias; sem payload/PII |
| `.env`, credenciais e chaves | acesso | secret | segredo | fora do ciclo de dados; revogar/rotacionar no offboarding |

`PUBLIC` é reservado a documentação e fixtures fictícias. `SECRET` nunca deve
entrar em logs, alertas, artefatos ou tabelas operacionais.

## Minimização

`payload_json` é necessário para aplicar diff e restaurar estado, mas não deve
ser copiado para logs, alertas ou novos stores. `source_row_number` é necessário
somente para rastreabilidade de evento não-tombstone. Hashes são referências
operacionais, não anonimização garantida. `error_summary` e `error_message`
devem conter somente categoria sanitizada; texto bruto de exceção é proibido.
Referências de fonte e execução usam prefixo/hash seguro, nunca IDs completos.

## Estado atual e histórico

`raw_current_rows` existe para a operação presente, tombstone/restore e diff;
não deve ser removida por retenção de histórico enquanto a fonte estiver ativa.
`raw_import_rows` é auditável e event-only: o purge futuro deve respeitar uma
janela de reconciliação, remover apenas eventos expirados e nunca quebrar o
estado atual ou uma investigação/hold. Tombstones e restores exigem preservar a
cadeia histórica dentro da janela escolhida.

## Observabilidade e alertas

Stdout/stderr, eventos estruturados e alertas guardam apenas campos allowlist:
severidade, componente, categoria, tentativas, duração e referências seguras.
A deduplicação atual é in-memory e não é incidente persistido. Se houver store
futuro, ele não pode conter células, payloads, PII, URL, token ou credencial.

## Offboarding e exclusão

1. Suspender a fonte e revogar/rotacionar credenciais fora do repositório.
2. Preservar apenas a evidência agregada exigida por hold aprovado.
3. Inventariar e apagar, mediante autorização humana, current, history, erros,
   requests, snapshots, artefatos, logs sob controle do projeto e backups locais.
4. Para projeto isolado por instituição, encerrar o projeto Supabase é decisão
   de infraestrutura separada; backups do provedor, Git, CI e workstations têm
   ciclos próprios e não são controlados automaticamente pelo aplicativo.
5. Registrar execução sanitizada, sem payload ou identidade pessoal.

## Ambientes e automação futura

Local/dev usa somente fixtures fictícias e pode limpar runtime ao fim do teste.
Staging segue a política técnica com autorização humana. Produção futura exige
prazo legal aprovado, hold, owner e evidência de purge. A opção simples é job
Python periódico em dry-run primeiro, com seleção por datas indexadas e relatório
agregado; SQL destrutivo ou scheduler do provedor dependem de ADR posterior.

## Evolução de schema local

A migration `20260825120000_add_retention_controls.sql` implementa localmente
lifecycle, legal hold e evidência agregada de purge. Ela não implementa seleção
de candidatos, scheduler, offboarding automático ou qualquer exclusão. Prazos
continuam em configuração externa versionada e dependem de aprovação humana.

## Gate de desenho de schema em 2026-08-25

O desenho mínimo foi concluído na
[ADR de retenção](decisions/20260825_retention_schema_design.md), sem criar
migration ou executar purge. Ele separa responsabilidades:

- prazos revisáveis ficam em configuração externa versionada por fonte;
- `data_sources` recebe futuramente um ciclo de vida explícito;
- `retention_holds` preserva ativação e liberação de hold institucional ou por
  fonte;
- `purge_runs` preserva aprovação, policy/dry-run digests, cortes e contagens
  agregadas, sem payload ou PII;
- `raw_current_rows` nunca participa de purge histórico e só pode ser eliminada
  por offboarding aprovado;
- `sync_runs` referenciada por current ou ainda necessária para reconciliação
  permanece protegida, mesmo além do prazo recomendado.

O dry-run futuro será read-only e não fará DML. Qualquer execução destrutiva
continua bloqueada até política humana aprovada, migration revisada, testes
locais e autorização específica.

## Validação local da migration 4 em 2026-08-25

As quatro migrations foram reaplicadas por reset exclusivamente local. Lifecycle
e coerência com `enabled`, hold global/por fonte, release, `purge_runs`, FKs,
índices, RLS, zero policies e grants mínimos passaram em PostgreSQL real. Todas
as fixtures de comportamento sofreram rollback; nenhum purge foi executado.

`raw_current_rows.last_sync_run_id` permanece `NO ACTION` e bloqueou a remoção
controlada de uma run referenciada. `service_role` pode apenas consultar holds e
evidências e não possui DELETE nas tabelas operacionais. Referências de ator e
reason codes aceitam somente tokens técnicos opacos, sem nome, e-mail ou login.

## Revisão read-only da migration 4 em 2026-08-27

A revisão anterior a staging rebaixou a migration para `requires_changes`. No
PostgreSQL local, hold específico ativo bloqueou somente a exclusão da linha de
`data_sources` pelo efeito combinado de `ON DELETE SET NULL` e do CHECK de
escopo. Hold institucional ativo não bloqueou essa exclusão; nenhum dos dois
escopos impediu transição para `offboarding`, e hold específico ativo não
impediu exclusão direta do histórico por owner/admin. O banco também não impede
gravação de runs/raw para uma fonte não ativa.

Holds liberados não criam bloqueio permanente: uma ou várias evidências
históricas liberadas sobreviveram à retirada local da fonte com FK nula e
`source_ref` preservada. A correção do bloqueio de hold/lifecycle deve ser
deliberada e novamente testada localmente; esta revisão não alterou o DDL nem
autorizou aplicação remota ou purge.

## Revalidação local após correção em 2026-08-27

A Migration 4 passou a bloquear no banco novas `sync_runs` de fontes não
ativas e qualquer exclusão de dados operacionais, offboarding, retirada da
fonte ou transição para `retired` quando houver hold institucional ou da fonte.
Hold não impede a suspensão operacional nem dry-run. Hold liberado deixa de
bloquear e preserva a referência técnica histórica quando a FK da fonte é
nulificada.

`purge_runs` não guarda mais JSONB para cutoffs ou contagens: cortes são
timestamps explícitos e contagens são colunas `bigint` não negativas. O banco
impõe as transições e a evidência terminal; política, aprovação humana e a
decisão de qualquer purge continuam `application_enforced`. Não existe executor
de purge, job ou scheduler nesta migration.

## Revisão final da Migration 4 em 2026-08-27

A revisão final reclassificou o DDL como `requires_changes`. Embora a evidência
já terminal seja imutável, a máquina permite que uma run destrutiva ainda
`planned` carregue sinais de execução sem aprovação/hold check, e permite uma
run `failed` com efeito agregado positivo sem início, executor ou aprovação. A
ordem entre `approved_at` e `finished_at` também não é garantida quando não há
`started_at`.

Holds já liberados não voltam a ativo em uma atualização posterior, mas o mesmo
statement que define `released_at` ainda consegue reescrever campos de ativação.
Os guards de destrutividade cobrem `DELETE`, não `TRUNCATE`, e não há serialização
institucional entre ativação concorrente de hold e uma operação destrutiva.
Nenhum desses achados executou purge; os probes usaram somente fixtures locais e
terminaram em rollback. O staging não foi consultado neste gate.

## Controles finais revalidados localmente em 2026-08-27

A Migration 4 corrigida impõe a máquina final: `planned`, `approved` exclusivo
do fluxo destrutivo, `running` com início/executor/hold check, e terminal
coerente. `failed` e `cancelled` pré-execução não carregam sinal ou contagem de
execução; se vierem de `running`, preservam os campos de execução, mas continuam
com contagens afetadas em zero porque a futura unidade de purge é transacional.
Somente `completed` pode ter efeito agregado positivo.

Ativação/liberação de hold e toda destrutividade concorrente usam advisory
transaction locks na ordem instituição e depois fonte. `TRUNCATE` operacional é
bloqueado diante de qualquer hold ativo; `TRUNCATE` das duas tabelas de evidência
administrativa é sempre rejeitado. Release é append-only desde o primeiro
statement e, após liberado, só aceita a nulificação de FK exigida pelo
offboarding. Isso não protege contra owner/superuser malicioso.

Essas são garantias `database_enforced`; aprovação humana, política, seleção de
candidatos e a execução de purge continuam `application_enforced`. Nenhum
executor, scheduler ou purge real existe. A revalidação usou somente Supabase
local, com 4/4 migrations e testes opt-in verdes; staging não foi acessado.
