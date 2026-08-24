# Monitoramento

`python -m sheets_supabase_sync.cli doctor` verifica configuracao, runtime, migrations e presenca de credencial sem revelar valores. Use `--format json` para automacao. Os codigos sao: 0 saudavel, 1 aviso, 2 falha.

O estado por fonte registra tentativas, ultimo sucesso/falha, falhas consecutivas, duracao, contagens e proximo horario. Alertas deterministas: primeira falha transitoria gera aviso; tres falhas, autenticacao/permissao invalida ou atraso maior que 4h30 geram criticidade; schema destrutivo e bloqueante.

Eventos estruturados usam somente identificadores, status, duracao, contagens e codigo de erro. URLs, tokens, senhas e payloads completos nao sao registrados.

## Eventos e alertas operacionais

`OperationalEvent` usa timestamp, componente, operação, resultado, severidade,
tentativa, categoria/código, duração, backoff e referências seguras de fonte e
execução. As severidades são `info`, `warning`, `error` e `critical`.
Retries e busy/deferred são `warning` e não alertam por padrão; falha final é
`error`; `ambiguous_outcome` é `critical` e exige reconciliação humana.

Alertas são separados da emissão de eventos, deduplicados por
componente/categoria/fonte segura e têm cooldown local configurável. O transporte
SMTP é opcional e configurado somente por ambiente; ausência ou falha dele não
interrompe a sincronização. Assunto e corpo não contêm payload, PII, URL, token,
senha ou texto bruto de exceção.

O `doctor` permanece uma verificação offline de configuração e runtime. O estado
`needs_reconciliation` é sinalizado pelo evento crítico `ambiguous_outcome`; uma
agregação persistente por fonte depende do scheduler e não foi criada neste gate.
