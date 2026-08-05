# Runbook

- **Sem permissao ou credencial revogada:** classifique como `authorization` ou `authentication`, interrompa apenas a fonte e corrija a credencial no mecanismo seguro.
- **Sheet ou aba inexistente:** classifique como `not_found`, confira `spreadsheet_id` e `sheet_name`.
- **Schema bloqueante:** revise o manifest e `schema_change_requests`; nao renomeie, remova coluna ou altere tipo automaticamente.
- **Supabase indisponivel ou migration ausente:** execute `doctor`, confira Supabase local e aplique migrations somente no ambiente local.
- **Falhas consecutivas:** investigue apos o terceiro alerta critico; as demais fontes permanecem independentes.
- **Snapshot corrompido:** preserve o arquivo para analise, restaure uma copia conhecida e execute dry-run.
- **Sincronizacao travada/duplicidade:** aguarde ou recuse a segunda execucao da mesma fonte; use advisory lock transacional quando o banco local estiver ativo.
- **Baseline aguardando deploy:** confirme que existe uma unica migration ativa, rode testes, lint e `supabase db push --dry-run`, e encaminhe o resultado para revisao humana. Nao aplique a baseline como parte de um diagnostico.
- **Historico de migrations divergente:** interrompa a implantacao; nao use `migration repair` ou `db reset --linked`. Compare o historico local e remoto e escale para revisao do responsavel.
- **Migration da PoC encontrada como ativa:** mova-a somente apos confirmar sua copia em `docs/history/initial-migrations-poc/`; arquivos historicos devem permanecer com extensao `.sql.txt` e nunca ser executados.
- **Recuperacao apos falha de deploy:** preserve a saida sanitizada, nao altere o remoto manualmente e verifique `migration list` antes de propor uma migration incremental. Uma baseline ja aplicada nunca deve ser reescrita retroativamente.
