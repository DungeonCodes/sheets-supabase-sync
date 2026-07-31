# Arquitetura

O pacote `sheets_supabase_sync` separa configuracao, normalizacao, hashing, snapshot, comparacao, SQL, artefatos e execucao. `synchronizer.py` apenas orquestra o dry-run. Dados de entrada permanecem em `data/`; estado local e artefatos ficam em `runtime/`, ignorados pelo Git.

As tabelas `raw_import_rows` e `mirror_records` preservam a origem em JSONB. `sync_runs`, `import_errors` e `schema_change_requests` fornecem trilha de auditoria. A view `active_mirror_records` oculta registros logicamente removidos.
