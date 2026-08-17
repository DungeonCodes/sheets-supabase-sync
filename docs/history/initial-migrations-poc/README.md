# Migrations iniciais da PoC

Estas migrations pertenciam à prova de conceito e nunca foram aplicadas ao projeto Supabase remoto.

- A primeira criava um modelo multitenant com organizações e projetos.
- A segunda substituía esse modelo por isolamento por instituição, mas removia estruturas com `DROP TABLE`.
- A terceira acrescentava saúde operacional e documentava a estratégia futura de advisory lock, dependendo da segunda.

Os três arquivos foram consolidados antes do primeiro deploy em uma baseline limpa. Os arquivos `.sql.txt` são históricos, não são descobertos pelo Supabase CLI e não devem ser executados.

Uma migration histórica ainda menciona `current_schema`. Essa ocorrência foi preservada intencionalmente para manter o registro fiel da PoC e não representa o schema executável atual. Na baseline ativa, o campo foi corrigido para `previous_schema` após a primeira tentativa de aplicação falhar e sofrer rollback completo.

A baseline corrigida foi aplicada com sucesso ao staging em 2026-08-05. As migrations históricas deste diretório continuaram inertes e nunca foram aplicadas.
