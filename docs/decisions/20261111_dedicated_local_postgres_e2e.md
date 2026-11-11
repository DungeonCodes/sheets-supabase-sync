# PostgreSQL dedicado para E2E local sintético

Para validar o pipeline e o dashboard sem depender da stack Supabase completa,
usar contêiner PostgreSQL dedicado, em loopback, com banco e volume próprios.
O cluster contém exclusivamente fixtures e não é staging nem produção. Papéis
com nomes usados pelas migrations são compatibilidade mínima, não prova de
equivalência com Supabase. O papel de dashboard é restrito por RLS a uma source
fixa; concede acesso a fatos dessa source, e a aplicação apresenta agregados.

O pacote está sujeito à revisão e aprovação humana antes de SQL de projeto. Os
testes de retenção com operações proibidas ficam fora da suíte dedicada; não são
considerados aprovados. Fixtures podem persistir após os testes. Sem reset,
limpeza física, exclusão de volumes ou acesso remoto. Resultados e limitações
devem ser registrados em `docs/local_sql_execution_review.md` e `docs/run_log.md`.
