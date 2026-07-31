# Regras do Repositorio

- Leia `docs/master_context.md` e `docs/agent_rules.md` antes de decidir regras de negocio.
- Nao use credenciais reais, hosts remotos nem dados reais em fixtures ou artefatos.
- Nao aplique SQL sem revisao humana; `DROP COLUMN`, `DELETE` fisico, renomeacoes e conversoes destrutivas sao proibidos automaticamente.
- Registre decisoes duraveis em `docs/decisions/` e execucoes relevantes em `docs/run_log.md`.
- Preserve `demandas_inicie` como repositório documental externo e somente leitura.
