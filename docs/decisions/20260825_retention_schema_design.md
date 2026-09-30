# ADR 20260825: desenho mínimo de schema para retenção

## Status e escopo

Decisão de arquitetura implementada e validada somente no PostgreSQL local pela
migration `20260825120000_add_retention_controls.sql`. A migration não implementa
purge e não autoriza exclusão. Os prazos citados são recomendações técnicas
configuráveis, não prazos legais. Nada foi aplicado ao staging.

## Schema atual relevante

| Tabela | Identidade e FKs | Datas e estado relevantes | Uso para retenção e limite atual |
| --- | --- | --- | --- |
| `data_sources` | PK `id`; unicidade por nome, tabela alvo e planilha/aba | `enabled`, datas de tentativa/sucesso/falha e `created_at`/`updated_at` | `enabled` agenda a fonte, mas não distingue suspensão, offboarding e retirada; não há hold |
| `sync_runs` | PK `id`; FK obrigatória para `data_sources` | `status`, `started_at`, `finished_at`, contagens e `snapshot_hash` | datas suportam corte, mas runs ainda podem ser referenciadas por history, errors e current |
| `raw_import_rows` | PK `id`; FKs obrigatórias para fonte e run; identidade única por run/fonte/chave | `imported_at`, `change_type`, `row_version` | suporta seleção temporal; eventos não possuem FK entre si |
| `raw_current_rows` | PK `id`; FK obrigatória para fonte; FK opcional `last_sync_run_id`; unicidade fonte/chave | `first_seen_at`, `last_seen_at`, `deleted_at`, `created_at`, `updated_at`, `is_deleted`, `version` | é estado operacional, não histórico expirável; a FK para a última run protege reconciliação |
| `import_errors` | PK `id`; FK obrigatória para fonte; FK opcional para run | `created_at` | suporta corte temporal, mas não possui estado de investigação |
| `schema_change_requests` | PK `id`; FK obrigatória para fonte | `status`, `created_at`, `reviewed_at` | requests pendentes não podem expirar; decisões concluídas podem usar `reviewed_at` |

Todas as FKs existentes usam o comportamento padrão restritivo, sem cascade ou
`SET NULL`. RLS está habilitado e não há policies permissivas. O histórico raw
concede apenas leitura e inserção a `service_role`; current concede leitura,
inserção e atualização, sem delete.

## Limitações demonstradas

O schema não representa ciclo de vida da fonte, legal hold, aprovação de purge,
versão da política usada nem evidência agregada da execução. `sync_runs` não deve
ser reutilizada: ela descreve ingestão e reconciliação de uma fonte, enquanto
purge possui aprovação, cortes, contagens e resultado próprios.

`raw_current_rows.last_sync_run_id` impede corretamente apagar uma run ainda
ancorada pelo estado atual. A futura rotina deve excluir essas runs da seleção;
trocar a FK para `ON DELETE SET NULL` reduziria a rastreabilidade e não faz parte
do desenho mínimo.

## Separação dos requisitos

### Indispensável no schema

- ciclo de vida explícito em `data_sources`;
- histórico de legal hold em nível institucional ou de fonte;
- entidade `purge_runs` separada de `sync_runs`;
- FKs restritivas, constraints de consistência e índices para scans;
- evidência agregada, aprovação e proveniência da política usada.

### Configuração Python externa e versionada

- dias por fonte para history, runs, errors, requests, logs e artefatos;
- janela técnica mínima de reconciliação;
- referência, versão e digest da política aprovada;
- tamanho de lote, orçamento de execução e scheduler;
- automação desabilitada por padrão.

Os valores recomendados atuais permanecem 180 dias para history e runs, 30
dias para errors e logs, 365 dias para requests concluídas e 7 dias para
artefatos locais. `raw_current_rows` é governada por ciclo de vida, não por
idade. Esses valores podem ser revisados e não declaram obrigação legal.

### Operacional ou documental

- definição jurídica dos prazos e bases legais;
- designação de aprovador e executor;
- revogação de credenciais e tratamento de backups;
- captura e guarda do relatório local de dry-run;
- resposta a falhas e revisão da evidência final.

## Política por fonte

Foram comparadas quatro opções:

| Opção | Vantagem | Risco | Decisão |
| --- | --- | --- | --- |
| colunas em `data_sources` | consulta simples | mistura contrato da fonte, valores jurídicos e versionamento; cresce uma coluna por classe | rejeitada |
| tabela própria de policy | histórico e joins fortes | nova entidade sem necessidade atual e fluxo de aprovação mais complexo | adiada |
| configuração externa versionada | revisão por diff, sem DDL para mudar prazo | o executor precisa validar referência/digest e congelar a policy usada | adotada |
| combinação mínima | schema guarda garantias; configuração guarda valores | exige contrato claro entre os dois lados | adotada |

A configuração de cada fonte deve fornecer uma referência estável, versão,
digest e prazos por tipo. `purge_runs` congela essa proveniência, os cortes
calculados e os agregados; não guarda payload, célula ou identificador bruto.

## Legal hold

É necessária uma tabela `retention_holds`, pois um booleano em `data_sources`
não preservaria ativações e liberações. O escopo mínimo cobre:

- instituição, aplicável a todas as fontes do projeto Supabase isolado;
- fonte específica;
- não cobre registro individual nesta etapa, pois isso exigiria armazenar
  identidades de linhas e aumentaria o risco de PII sem caso comprovado.

Um hold ativo sempre vence qualquer prazo e bloqueia purge histórico,
offboarding destrutivo e retirada da fonte. Ativação e liberação são operações
humanas controladas pelo owner/admin do banco, nunca pelo sincronizador. Cada
registro preserva escopo, referência segura da fonte quando aplicável,
`reason_code` controlado, referências seguras de quem ativou/liberou e datas.
Texto livre, payload, célula, credencial e identidade pessoal não são aceitos.

Somente uma hold institucional ativa e uma hold ativa por fonte são permitidas.
A consistência entre escopo, FK, datas e ator de liberação é protegida por
constraints. Purge e alteração de hold compartilham um advisory lock
institucional de retenção; purge também usa o advisory lock já adotado pela
sincronização da fonte. Isso impede a corrida entre seleção e ativação de hold.

`service_role` recebe somente leitura dessa tabela. Ativação e liberação usam
um canal administrativo revisado. Offboarding pode avançar até inventário, mas
não pode apagar dados nem concluir enquanto houver hold aplicável.

## Ciclo de vida e proteção de current

A futura migration adiciona a `data_sources`:

- `lifecycle_status`: `active`, `suspended`, `offboarding` ou `retired`;
- `lifecycle_changed_at`;
- `lifecycle_reason_code`, opcional e controlado;
- `lifecycle_changed_by_ref`, referência segura do responsável.

Os nomes descrevem estados técnicos:

| Estado | Sincronização | Retenção histórica | Remoção de current |
| --- | --- | --- | --- |
| `active` | permitida | permitida quando expirada, aprovada e sem hold | proibida |
| `suspended` | proibida e reversível | permitida nas mesmas condições de active | proibida |
| `offboarding` | proibida; credenciais já devem estar revogadas | somente por execução de offboarding aprovada | permitida apenas nessa execução e sem hold |
| `retired` | proibida | não restam dados operacionais no escopo aprovado | já concluída e evidenciada |

`enabled` permanece por compatibilidade, mas deve ser projeção coerente do
estado: verdadeiro apenas em `active`; os demais estados exigem falso. A futura
migration deve classificar fontes existentes habilitadas como `active` e as
desabilitadas como `suspended` antes de ativar a constraint.

Rotina histórica jamais inclui `raw_current_rows`, inclusive tombstones. A
remoção de current é uma operação separada, exclusivamente no offboarding,
após hold check e aprovação humana. A transição para `retired` exige current
vazio e evidência final; essa invariável entre tabelas é verificada pela unidade
transacional, pois um CHECK não pode consultar outra tabela.

## Fluxo de purge auditável

1. **Retention scan:** carregar fonte, configuração aprovada e holds; adquirir
   locks; calcular candidatos somente por metadados.
2. **Candidate selection:** aplicar cortes, estados terminais, janela de
   reconciliação e exclusões por FK/current.
3. **Dry-run:** transação read-only e zero DML; emitir apenas contagens, cortes,
   referências seguras e digest determinístico. Artefato local é opcional e
   segue retenção de 7 dias.
4. **Human approval:** aprovar o digest exato, a versão da policy e o escopo.
   Criar `purge_runs` somente depois da aprovação.
5. **Purge:** reutilizar o UUID cliente da purge run, readquirir locks, reler
   hold e candidatos, abortar em divergência, apagar na ordem segura e concluir
   evidência na mesma transação dos deletes.
6. **Aggregate evidence:** guardar somente cortes, contagens por entidade,
   policy/dry-run digests, outcome, duração e referências seguras.

Falha transacional reverte deletes e conclusão. Uma atualização sanitizada da
run pode registrar a falha após rollback. Retry reutiliza o mesmo UUID e uma
run `completed` é no-op, assegurando idempotência.

## Regras por entidade

### `raw_import_rows`

O corte usa `imported_at`, fonte e run terminal. Nenhum evento de run ainda
dentro da janela de reconciliação é candidato. Insert, update, tombstone e
restore recebem a mesma regra; não há FK entre eventos que impeça exclusão.

A exclusão torna a cadeia anterior ao corte não reexecutável e pode deixar
lacunas de versão. Isso é consequência explícita de retenção: current continua
autoritativo, a auditoria detalhada vale apenas dentro da janela e a evidência
agregada registra o que foi removido. Purge não pode alegar reconstrução total
do histórico após o corte.

### `sync_runs`

Runs são apagadas por último e somente quando:

- possuem estado terminal e `finished_at`;
- estão além tanto do prazo configurado quanto da janela técnica de
  reconciliação;
- não possuem `raw_import_rows` ou `import_errors` referenciando-as;
- não são referenciadas por `raw_current_rows.last_sync_run_id`.

Assim, uma run ancorada por current pode permanecer além de 180 dias. Esse é um
limite de integridade deliberado. Runs `planned`/`running`, outcomes ainda
ambíguos ou divergentes nunca entram em purge automático. A janela de
reconciliação é configurável e deve ser pelo menos o maior prazo operacional
aprovado para resolver outcomes ambíguos; seu valor definitivo é decisão
humana, não prazo legal.

### `import_errors`

O corte usa `created_at`. Erros expirados podem ser removidos antes da run pai.
Uma investigação aberta deve ativar hold no escopo mínimo disponível. O produtor
continua proibido de colocar payload ou mensagem bruta; a existência atual de
`payload_json` não autoriza seu uso.

### `schema_change_requests`

Requests `pending` nunca são candidatas. Apenas `approved` ou `rejected`, com
`reviewed_at` além do corte configurado, podem ser removidas. A evidência de
purge mantém somente contagem agregada; decisões contratuais que precisem de
guarda maior devem receber hold ou prazo revisado.

## Offboarding

1. transicionar `active`/`suspended` para `offboarding` e tornar `enabled=false`;
2. parar scheduler e revogar credenciais fora do banco;
3. verificar hold institucional e da fonte;
4. executar dry-run agregado incluindo current, history, runs, errors, requests
   e artefatos locais;
5. obter aprovação humana do digest;
6. em canal administrativo, remover current, depois errors/history/requests e,
   por último, runs, respeitando FKs;
7. confirmar escopo vazio, registrar evidência agregada e marcar `retired`;
8. tratar `data_sources`, backups e encerramento do projeto em políticas
   separadas.

Hold pode suspender o passo destrutivo por tempo indefinido. Rollback da
transição antes do purge pode retornar a fonte a `suspended`; depois de deletes,
restauração depende de backup aprovado, não de rollback de schema.

## Entidades propostas para a migration 4

Nome sugerido, sem criar o arquivo:
`20260825120000_add_retention_controls.sql`.

As alterações conceituais em `data_sources` são aditivas:

- `lifecycle_status` texto, inicialmente com default `active` e, ao final do
  backfill, obrigatório e limitado aos quatro estados definidos;
- `lifecycle_changed_at` timestamptz obrigatório, com default de tempo atual;
- `lifecycle_reason_code` e `lifecycle_changed_by_ref` opcionais para fonte
  ativa, mas obrigatórios por CHECK nos demais estados;
- backfill de fontes habilitadas para `active` e desabilitadas para
  `suspended`, antes de exigir equivalência entre `enabled` e lifecycle;
- CHECK que permite `enabled=true` somente e sempre em `active`.

Não são adicionados prazos a `data_sources`, e nenhuma coluna aplicada é
renomeada ou removida.

### `retention_holds`

- PK UUID com geração padrão;
- escopo textual obrigatório e controlado `institution`/`source`;
- FK opcional para `data_sources`, com `ON DELETE SET NULL` e constraint que
  impede remover a fonte enquanto o hold de fonte estiver ativo;
- `source_ref` segura obrigatória no escopo de fonte;
- `reason_code`, `placed_at` e `placed_by_ref` obrigatórios; `placed_at` usa o
  tempo atual por default;
- `released_at`, `released_by_ref` e `release_reason_code` todos nulos enquanto
  ativo e todos preenchidos na liberação;
- constraints de ativação/liberação e unicidade parcial de hold ativo;
- índices parciais para hold institucional e por fonte ativos.

### `purge_runs`

- PK UUID obrigatória, fornecida pelo cliente e reutilizada em retries;
- FK opcional para `data_sources` com `ON DELETE SET NULL`, mais `source_ref`
  segura para preservar evidência após retirada;
- `source_ref`, tipo `retention`/`offboarding` e status controlado obrigatórios;
  os status aceitos são `approved`, `running`,
  `completed`, `failed` ou `blocked`;
- referência, versão e digest da policy e digest do dry-run obrigatórios;
- cortes e contagens candidatas em objetos JSONB agregados obrigatórios, sem
  default implícito; contagens removidas começam como objeto vazio;
- `approved_at`/`approved_by_ref`, `started_at`/`finished_at`,
  `executed_by_ref`, `hold_checked_at`, `evidence_digest` e código de erro
  sanitizado; campos de execução/finalização ficam nulos até a transição
  correspondente;
- checks de tipos JSON, ordem temporal e coerência de status;
- índices por fonte/data e por status ainda executável.

Não haverá tabela de policy nesta migration. Não haverá tabela de candidatos,
IDs de linhas, payloads, células ou PII na evidência.

## Índices adicionais nas tabelas existentes

- `sync_runs(data_source_id, finished_at)` parcial para runs terminais com
  `finished_at` não nulo;
- `schema_change_requests(data_source_id, reviewed_at)` parcial para status
  `approved`/`rejected`;
- os índices atuais de history por `imported_at`, errors por `created_at` e
  current por `last_sync_run_id` já atendem os scans e proteções necessários;
- nenhum índice isolado de `lifecycle_status` é necessário antes de volume
  multi-fonte demonstrar uso.

## FKs, delete behavior e grants

As FKs operacionais existentes permanecem restritivas. Em especial,
`raw_current_rows.last_sync_run_id` não muda. As novas referências de evidência
para fonte usam `SET NULL` somente quando uma `source_ref` segura preserva o
vínculo; hold ativo impede a remoção da fonte por constraint.

RLS deve ser habilitado nas duas novas tabelas, com zero policies. A migration
deve revogar privilégios de `PUBLIC`, `anon`, `authenticated` e `service_role`
antes de grants explícitos. `anon` e `authenticated` permanecem sem acesso.
`service_role` recebe apenas SELECT em holds e purge runs; não recebe DELETE em
nenhuma tabela. Hold, lifecycle, aprovação e purge usam owner/admin controlado.

Como `service_role` hoje possui grant amplo em `data_sources`, a migration deve
propor grants por coluna: leitura necessária, inserção apenas dos campos do
contrato da fonte e atualização apenas de agenda/health. Campos de lifecycle
ficam fora do update operacional. A lista exata será validada contra o adaptador
antes da migration; não se cria permissão permanente de delete para facilitar
o job.

## Rollback futuro

Antes de uso produtivo e sem purge executado, o rollback de DDL pode desabilitar
o worker, remover grants/índices/constraints novos, remover `purge_runs` e
`retention_holds` vazias e retirar as colunas de lifecycle após validação humana.
Como remoção de coluna/tabela é destrutiva, isso exige migration reversa revisada
e nunca é automático neste repositório.

Depois de qualquer purge, rollback de migration não restaura dados. Somente um
backup abrangido por política aprovada poderia restaurá-los, com procedimento
separado e reconciliação. A medida segura de rollback operacional é desabilitar
o scheduler/worker e preservar evidência.

## Plano obrigatório antes de aplicar a migration

- testes estruturais offline da migration, sem DDL destrutivo e com digest das
  migrations aplicadas preservado;
- fonte `active` e `suspended`: current nunca candidato;
- dado dentro da retenção protegido e expirado selecionado;
- hold institucional e de fonte bloqueiam qualquer delete;
- dry-run usa transação read-only e não altera nenhuma tabela;
- offboarding exige estado, credencial revogada como gate operacional,
  aprovação e ausência de hold;
- history purge não remove current e respeita todos os tipos de evento;
- runs referenciadas por history, errors ou `last_sync_run_id` permanecem;
- run ambígua/não terminal e janela de reconciliação permanecem;
- requests pendentes permanecem e requests concluídas seguem o corte;
- purge repete o mesmo UUID sem duplicar evidência ou efeito;
- concorrência entre sync, purge e ativação de hold é serializada pelos locks;
- falha em cada etapa reverte deletes e preserva estado consistente;
- catálogo PostgreSQL local confirma PKs, FKs, CHECKs, índices, RLS, zero
  policies e grants negativos para `anon`, `authenticated` e `service_role`;
- ciclo local completo com fixtures fictícias e contagens agregadas;
- nenhum staging antes de revisão humana do DDL e dos testes locais.

## Custo e complexidade

O desenho adiciona duas tabelas pequenas e quatro colunas de lifecycle, sem
dependência Python ou serviço pago. O scan usa índices existentes mais dois
índices parciais. Não exige scheduler para validar a migration; operação manual
é suficiente no primeiro gate. Um scheduler futuro é decisão separada.

Configuração externa evita uma terceira tabela e suporta múltiplas fontes. O
custo dominante continuará sendo o volume de history, não a evidência agregada.

## Decisões humanas ainda abertas

- prazos definitivos por tipo e janela técnica de reconciliação;
- responsável por aprovar policy, purge, hold e liberação;
- reason codes e referência segura de atores;
- política de backups, restore e holds sobre backups;
- checklist e prazo de offboarding/retirada de `data_sources`;
- autorização de produção, scheduler e canal administrativo de purge.

Essas decisões bloqueiam execução destrutiva, mas não o desenho configurável.

## Implementação local em 2026-08-25

A migration 4 materializou as duas tabelas e o lifecycle aprovados. Para atender
ao contrato executável do gate, `purge_runs` também representa dry-runs com
estado fechado; dry-run exige contagens afetadas vazias. A nomenclatura
`data_source_id` foi preservada por coerência com o schema existente.

Os grants amplos herdados da baseline em `data_sources`, `sync_runs`,
`import_errors` e `schema_change_requests` foram reduzidos ao uso real do
sincronizador. `service_role` não recebe DELETE e possui somente SELECT nas duas
novas tabelas. Referências de ator e reason codes são tokens técnicos opacos.

Reset, migration list e lint foram executados apenas localmente. Quatorze testes
PostgreSQL validaram lifecycle, holds, purge evidence, FKs, catálogo, RLS,
policies e grants, sempre com rollback das fixtures. As migrations 1–3 foram
protegidas por digest e não mudaram. Nenhum purge foi executado.

## Consequência e próximo gate

A necessidade de migration está demonstrada: lifecycle, hold e evidência de
purge não existem hoje. O desenho mínimo preserva current, FKs, reconciliação
ambígua e menor privilégio.

Classificação: `retention_schema_local_validated`.

Próximo gate único: revisão humana do DDL, grants e evidência local antes de
qualquer autorização separada para staging. Isso não autoriza purge.

## Revisão técnica read-only em 2026-08-27

A revisão humana do gate encontrou que a implementação não materializa no
banco a regra declarada nas linhas de desenho sobre hold e operação destrutiva.
O `ON DELETE SET NULL` combinado com `retention_holds_scope_consistent` bloqueia
somente a exclusão da linha de `data_sources` quando existe hold específico
ativo. Um hold institucional ativo não bloqueia essa exclusão, e nem hold
institucional nem hold específico impedem a transição para `offboarding` ou a
exclusão direta de dados-filhos por um owner/admin. Holds específicos liberados
continuam permitindo retirar a fonte e preservam `source_ref`, inclusive com
vários registros históricos.

Também foi confirmado que a equivalência entre `enabled` e lifecycle fecha os
estados da linha, mas não impede no banco iniciar `sync_runs` ou gravar raw para
uma fonte não ativa. O adaptador PostgreSQL atual localiza a fonte sem filtrar
`enabled` ou `lifecycle_status`; essa proteção não pode ser considerada
garantida pela aplicação existente.

Os CHECKs de `purge_runs` protegem status enumerado, pares de aprovação,
terminais com `finished_at`/`outcome_code`, ordem entre início e fim e dry-run
sem contagem afetada. Eles não exigem executor ou `hold_checked_at`, aceitam
aprovação posterior ao término e garantem apenas que os agregados JSONB sejam
objetos; valores não negativos, chaves allowlist e ausência de PII dependem do
produtor administrativo.

O staging foi consultado em transação read-only: mantém 3 migrations, a
Migration 4 não está aplicada, e a única fonte está habilitada, portanto o
backfill projetado é compatível com o estado observado. Nenhuma escrita remota,
DDL, purge, sync ou acesso Google ocorreu.

Classificação da revisão: `requires_changes`.

Próximo gate único: revisar explicitamente o DDL e os testes para que holds
ativos e lifecycle não ativo sejam barreiras efetivas antes de repetir toda a
validação local e a revisão read-only. A aplicação em staging permanece não
autorizada.

## Correção e revalidação local em 2026-08-27

A própria migration 4 foi corrigida antes de qualquer aplicação remota. O banco
agora guarda a criação de `sync_runs`: uma fonte só aceita nova execução quando
`enabled=true` e `lifecycle_status='active'`. O repositório PostgreSQL consulta
os mesmos dois campos antes de iniciar a run e retorna `source_inactive`, não
repetível, para `suspended`, `offboarding` ou `retired`.

`retention_hold_applies(uuid)` centraliza o hold institucional ou específico
ativo. Triggers SECURITY INVOKER, sem SQL dinâmico, bloqueiam `offboarding`,
`retired`, exclusão de `data_sources` e exclusões diretas de current, history,
errors, requests ou runs enquanto o hold for aplicável. A liberação remove o
bloqueio; evidência de hold liberado só pode receber o `SET NULL` de sua FK e
não é imutável contra o owner/admin do banco, que permanece trust boundary.

`purge_runs` substituiu JSONB de cortes/contagens por timestamps e contagens
`bigint` explícitos, não negativos. O guard de transição exige início/executor,
aprovação e hold check para execução destrutiva, impede hold ativo em
`approved`/`running`/`completed`, fecha transições e torna evidência terminal
imutável, exceto a nulificação da FK necessária para preservar referência após
retirada legítima da fonte.

`database_enforced`: lifecycle para novas runs, hold aplicável, transições,
temporalidade, executor/hold check, contagens tipadas/não negativas, RLS e
grants. `application_enforced`: autorização humana, política/prazos, conteúdo
operacional dos reason codes opacos e a decisão de executar qualquer purge.
O reset e os testes PostgreSQL foram exclusivamente locais; staging não foi
consultado nem alterado.

## Revisão técnica final antes de staging em 2026-08-27

A revisão final encontrou lacunas adicionais na própria Migration 4 e a
classificou como `requires_changes`. Probes PostgreSQL locais, sempre revertidos,
comprovaram que uma run destrutiva ainda pode permanecer `planned` com
`started_at` e executor, sem aprovação nem `hold_checked_at`; também pode ir de
`planned` para `failed` com contagem afetada positiva e nenhuma evidência de
execução. Em uma run terminal `failed`, `approved_at` ainda pode ficar posterior
a `finished_at` quando `started_at` é nulo.

O guard de holds torna a linha imutável somente quando `OLD.released_at` já está
preenchido. Assim, a própria atualização que libera o hold ainda pode reescrever
`reason_code` e referências de ativação. Além disso, os guards destrutivos são
triggers de `DELETE`, sem trigger de `TRUNCATE`, e a Migration 4 não implementa
o advisory lock institucional descrito como requisito do executor futuro.

Continuam `database_enforced`: lifecycle de novas runs, holds já visíveis para
os `DELETE`s e transições protegidas, contagens não negativas, RLS/grants e
imutabilidade depois que a evidência já é terminal/liberada. A coerência completa
da criação da evidência terminal, o congelamento dos campos de ativação durante
o release e a serialização hold versus destrutividade ainda não são garantidas
pelo banco. O staging não foi acessado porque o gate local deixou de estar verde.

## Correção final local dos controles de retenção em 2026-08-27

A própria Migration 4 foi corrigida novamente, sem criar Migration 5. A máquina
de `purge_runs` agora distingue estados pré-execução de execução efetiva:
`planned` não aceita aprovação, início, executor, hold check, outcome ou efeito;
`approved` é exclusivo de execução destrutiva e ainda não contém efeito;
`running` exige início, executor e hold check; `completed` só vem de `running`.
`failed` e `cancelled` podem encerrar antes da execução com zero efeito, ou
após `running` preservando a evidência de execução. Como o executor futuro é
transacional, ambos os terminais de falha/cancelamento mantêm contagens afetadas
em zero; apenas `completed` pode registrar efeito persistido.

A transição de release agora acrescenta somente os três campos de liberação e
nunca reescreve a ativação. Depois de liberado, o hold é imutável, salvo a
nulificação da FK por retirada legítima da fonte. A disciplina de lock é
`instituição -> fonte`: ativação/liberação de hold, offboarding, retired, delete
de fonte, deletes protegidos e evidência destrutiva usam o mesmo advisory
transaction lock. A serialização institucional é deliberada; fontes diferentes
não recebem um segundo lock específico em comum além desse lock global.

`DELETE` continua protegido por fonte; `TRUNCATE` recebe trigger statement-level
nas seis tabelas operacionais e é bloqueado por qualquer hold ativo. `TRUNCATE`
de `retention_holds` ou `purge_runs` é sempre rejeitado para preservar a trilha
administrativa. `database_enforced` cobre essa máquina, release append-only,
locks, triggers, formato, RLS e grants. `application_enforced` continua cobrindo
aprovação humana, policy/prazos, seleção e execução real do purge e o significado
não pessoal das referências. Owner/superuser permanece trust boundary.

Três resets locais aplicaram 4/4 migrations; os 24 testes PostgreSQL opt-in,
catálogo e lint passaram. Não houve staging, Google, linked, push ou purge real.
Classificação: `retention_schema_local_final_validated`.

## Aplicação controlada no staging em 2026-08-31

Após preflight local verde e dry-run que listou exclusivamente a Migration 4,
`20260825120000_add_retention_controls.sql` foi aplicada uma única vez ao
staging pelo fluxo oficial. O histórico remoto passou a 4/4 e o lint remoto não
encontrou erros. A inspeção posterior ocorreu em transação explicitamente
`READ ONLY`.

O backfill classificou a única fonte habilitada como `active`, sem metadados de
suspensão. As tabelas de retenção e purge permanecem vazias. O catálogo remoto
confirmou as nove funções SECURITY INVOKER, os dezoito triggers, RLS habilitado
sem policies, grants mínimos, os cinco índices de retenção e a FK restritiva de
`raw_current_rows.last_sync_run_id`. Os agregados raw permaneceram inalterados;
nenhum purge, hold, offboarding, sync ou acesso Google ocorreu neste gate.

Classificação: `retention_schema_staging_applied_validated`. Executor, scheduler,
canal administrativo e decisão jurídica continuam fora do escopo desta migration.
