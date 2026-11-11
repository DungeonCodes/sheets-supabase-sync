# Inspeção local de evidências

`node drafts/github-clock-recurrence/inspect-evidence.mjs < evidence.json` lê JSON
local, não busca dados, não faz alterações e imprime somente campos permitidos. O
arquivo é um array dos eventos previamente sanitizados com `kind` adicionado:

* `clock`: registro `DISPATCH_ACCEPTED` do clock com `clock_run_id`,
  `executor_run_id`, `at`, `clock_branch`, `target_branch`, `expected_dev_sha` e
  `executor_sha`.
* `executor`: resumo agregado do executor, com `mode`, IDs, SHA, timestamp, `state`
  e os sete contadores emitidos pelo wrapper.
* `run`: metadados read-only de GitHub para o mesmo ID: `id`, `head_branch`,
  `head_sha`, `event`, `run_attempt`, `status`, `conclusion`, `updated_at`.

Nenhuma conexão é feita pelo programa. Ausências, erro de JSON, divergências,
IDs em conflito e execuções incompletas não contam como sucesso. Duplicatas exatas
são marcadas; eventos contraditórios são ambíguos. Entrada limitada a 5 MiB. A
última execução válida é calculada somente entre sucessos correlacionados, sem
falhas ou busy; não demonstra reconciliação com o banco. O modo manual anterior
não envia clock_run_id ao executor e exige correlação externa/revisão humana; o
inspector não presume esse vínculo. Para dados incompletos, o processo retorna 1.

`assessTick` só compara horário esperado, observado e tolerância fornecidos por
fonte independente. Este módulo não é monitor externo e não verifica silêncio por
conta própria. Usuário deve inspecionar resultados/IDs e reconciliar no piloto.
