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

## Necessidade de evolução

O schema atual é suficiente para auditoria e dry-run de elegibilidade, mas não
para purge/offboarding automatizado seguro. Antes de implementar, propor
migration revisada para retenção/hold e auditoria agregada de exclusão, índices
por data/fonte, RLS/grants mínimos e rollback que desabilite o job sem restaurar
dados apagados. Nenhuma migration é criada por esta política.

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
