# Roadmap

## Fase 1

- Sincronizador Python, fixtures, fontes isoladas por instituicao e validacao offline.
- Contratos de fonte, diagnostico `doctor`, regras de alerta, logging seguro e testes offline por categoria.
- Baseline institucional consolidada, lintada e validada em dry-run; aplicacao ainda pendente de revisao humana.

## Pendente local

- Docker, `psql`, Supabase local, `db reset`, execucao real das migrations, rollback, advisory lock, concorrencia e E2E local.

## Fase 2

- Aplicacao revisada da baseline no Supabase de homologacao, API real do Google Sheets e planilha piloto ficticia/anonimizada.

## Fase 3

- Interface Next.js, execucao manual, acompanhamento de sincronizacoes e dashboard.

## Fase futura

- Agendamento, filas e retentativas; avaliar Inngest apenas se volume e concorrencia justificarem. Nao ha scheduler implantado nesta fase.
