# 2026-10-21 — preparo de publicacao GitHub Clock

Gate GITHUB_CLOCK_SCHEDULE_PUBLICATION_PREPARATION, offline, YELLOW.
Recomendar SHA aprovado explicitamente para piloto, sem atualizacao automatica;
clock confere dev e filho candidato valida github.sha antes de checkout/credenciais.
Manter revisao controlada de dev como condicao: guard nao protege contra sua remocao.
Manual preservado, scheduled com opt-in separado ausente por padrao. Proposta
60 minutos NAO aprovada; nenhuma expressao cron ativa adicionada.

Correcao CLI isolada em drafts: return 1 apos resumo se sources_failed>0, sem
interromper outras fontes; infraestrutura continua 2, no_changes/busy/no due 0.
Executor candidato publica apenas agregados, alerta falha parcial por exit, nunca
resumo detalhado de fontes. Modelo de observabilidade nao e monitor ativo.
Propor notificacoes Actions e verificacao humana independente a cada 2h na janela
do piloto; SLA/dono/tolerancias ainda dependem de aprovacao. Nao configurar alertas.

Plano, rollback, limites, preflight renovado, testes e riscos:
`drafts/github-clock-recurrence/PUBLICATION_REVIEW.md`.
Proximo gate: GITHUB_CLOCK_SCHEDULE_PUBLICATION_REVIEW. Nenhum workflow operacional
ou src modificado; nenhum remoto escrito; gates GREEN nao repetidos.
