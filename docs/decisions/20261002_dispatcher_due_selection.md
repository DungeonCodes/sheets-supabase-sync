# Decisão 20261002: seleção central de fontes vencidas

O dispatcher staging consulta `data_sources` e deriva a última sincronização
válida de `sync_runs` com `status='applied'` e `finished_at` preenchido. O
intervalo continua sendo `sync_interval_minutes` da configuração versionada.

Uma fonte é elegível somente quando sua identidade persistida coincide com a
configuração, `enabled` está ativo e `lifecycle_status` é `active`. Sem run
aplicada ela está vencida; caso contrário, vence ao completar o intervalo. Uma
fonte inativa ou ainda não vencida é pulada. Divergência ou ausência no estado
remoto falha fechada. Falhas anteriores não mudam silenciosamente a política de
due.

Não foi criada migration: `sync_runs` já contém informação confiável de sucesso
e término. A migration 5 não foi alterada. A seleção usa transação PostgreSQL
`READ ONLY`; `--dry-select` não chama Google nem o core de escrita.

O GitHub Actions mantém apenas `workflow_dispatch`, com concorrência serializada
e timeout de 20 minutos. Não há `schedule`, Supabase Cron, token GitHub ou
segredo versionado.
