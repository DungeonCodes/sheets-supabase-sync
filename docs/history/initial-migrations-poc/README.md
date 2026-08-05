# Migrations iniciais da PoC

Estas migrations pertenciam à prova de conceito e nunca foram aplicadas ao projeto Supabase remoto.

- A primeira criava um modelo multitenant com organizações e projetos.
- A segunda substituía esse modelo por isolamento por instituição, mas removia estruturas com `DROP TABLE`.
- A terceira acrescentava saúde operacional e documentava a estratégia futura de advisory lock, dependendo da segunda.

Os três arquivos foram consolidados antes do primeiro deploy em uma baseline limpa. Os arquivos `.sql.txt` são históricos, não são descobertos pelo Supabase CLI e não devem ser executados.
