# Runbook

- **Sem permissao ou credencial revogada:** classifique como `authorization` ou `authentication`, interrompa apenas a fonte e corrija a credencial no mecanismo seguro.
- **Sheet ou aba inexistente:** classifique como `not_found`, confira `spreadsheet_id` e `sheet_name`.
- **Schema bloqueante:** revise o manifest e `schema_change_requests`; nao renomeie, remova coluna ou altere tipo automaticamente.
- **Supabase indisponivel ou migration ausente:** execute `doctor`, confira Supabase local e aplique migrations somente no ambiente local.
- **Falhas consecutivas:** investigue apos o terceiro alerta critico; as demais fontes permanecem independentes.
- **Snapshot corrompido:** preserve o arquivo para analise, restaure uma copia conhecida e execute dry-run.
- **Sincronizacao travada/duplicidade:** aguarde ou recuse a segunda execucao da mesma fonte; use advisory lock transacional quando o banco local estiver ativo.
