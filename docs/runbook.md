# Runbook

- **Sem permissao ou credencial revogada:** classifique como `authorization` ou `authentication`, interrompa apenas a fonte e corrija a credencial no mecanismo seguro.
- **Sheet ou aba inexistente:** classifique como `not_found`, confira `spreadsheet_id` e `sheet_name`.
- **Schema bloqueante:** revise o manifest e `schema_change_requests`; nao renomeie, remova coluna ou altere tipo automaticamente.
- **Supabase indisponivel ou migration ausente:** execute `doctor`, confira Supabase local e aplique migrations somente no ambiente local.
- **Falhas consecutivas:** investigue apos o terceiro alerta critico; as demais fontes permanecem independentes.
- **Snapshot corrompido:** preserve o arquivo para analise, restaure uma copia conhecida e execute dry-run.
- **Sincronizacao travada/duplicidade:** aguarde ou recuse a segunda execucao da mesma fonte; use advisory lock transacional quando o banco local estiver ativo.
- **Mudanca apos a baseline:** nunca edite a migration `20260804000000` ja aplicada. Crie uma nova migration incremental, rode testes, lint e dry-run e obtenha revisao humana antes do deploy.
- **Historico de migrations divergente:** interrompa a implantacao; nao use `migration repair` ou `db reset --linked`. Compare o historico local e remoto e escale para revisao do responsavel.
- **Migration da PoC encontrada como ativa:** mova-a somente apos confirmar sua copia em `docs/history/initial-migrations-poc/`; arquivos historicos devem permanecer com extensao `.sql.txt` e nunca ser executados.
- **Recuperacao apos falha de deploy:** preserve a saida sanitizada, nao altere o remoto manualmente e verifique `migration list` antes de propor uma migration incremental. Uma baseline ja aplicada nunca deve ser reescrita retroativamente.
- **Erro 42601 em identificador SQL:** interrompa sem retry, confirme rollback por `migration list` e inspecao somente leitura, corrija o identificador no validador central e repita testes, lint e dry-run. A tentativa de 2026-08-04 foi corrigida com `previous_schema`; a baseline corrigida foi aplicada com sucesso em 2026-08-05.
