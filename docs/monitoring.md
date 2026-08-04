# Monitoramento

`python -m sheets_supabase_sync.cli doctor` verifica configuracao, runtime, migrations e presenca de credencial sem revelar valores. Use `--format json` para automacao. Os codigos sao: 0 saudavel, 1 aviso, 2 falha.

O estado por fonte registra tentativas, ultimo sucesso/falha, falhas consecutivas, duracao, contagens e proximo horario. Alertas deterministas: primeira falha transitoria gera aviso; tres falhas, autenticacao/permissao invalida ou atraso maior que 4h30 geram criticidade; schema destrutivo e bloqueante.

Eventos estruturados usam somente identificadores, status, duracao, contagens e codigo de erro. URLs, tokens, senhas e payloads completos nao sao registrados.
