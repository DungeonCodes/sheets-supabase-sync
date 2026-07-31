# Seguranca

`.env` e dados de `data/` sao ignorados pelo Git. Use apenas `.env.example` como referencia e jamais inclua tokens, senhas, URLs privadas ou dados pessoais em artefatos versionados. A varredura de artefatos bloqueia padroes comuns de segredo.

O `service_role` pertence exclusivamente ao backend e nunca ao cliente. RLS esta habilitado nas tabelas, sem policies permissivas nesta fase; as regras de leitura dependem do futuro modelo de tenancy. O aplicador exige `apply-local`, URL explicita e `psql`; aceita somente loopback, salvo host de desenvolvimento explicitamente permitido. A URL nunca e registrada. Nao ha `DELETE` fisico, `DROP COLUMN`, renomeacao ou conversao destrutiva automatica: todos viram pendencias humanas.
