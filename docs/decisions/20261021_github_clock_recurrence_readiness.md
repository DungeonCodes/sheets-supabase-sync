# 2026-10-21 — recorrencia GitHub Clock preparada offline

Adotar desenho main clock -> dispatch fixo dev -> dispatcher Python -> staging.
Separar autorizacao manual validada da futura STAGING_CLOCK_SCHEDULE_ENABLED,
fail-closed e ausente por padrao. Propor revisao aprovada atualizada por promocao,
nao por tick, em STAGING_CLOCK_APPROVED_DEV_SHA; ambas variaveis nao criadas.
Manter zero retries e locks/elegibilidade existentes; nao prometer exactly-once.

Status YELLOW: politica final de revisao/protecao e corrida de dev, cadencia/SLA,
alerta de falha parcial, privacidade de logs e deteccao de silencio pendentes.
Nenhum workflow operacional modificado. Candidato, baseline, observador modelo,
testes e procedimentos em drafts/github-clock-recurrence/README.md.
Contexto mestre local e esqueleto; nenhuma nova regra de negocio inferida dele.
Escopo e criterios deste desenho derivam do gate explicito fornecido pelo usuario.
Proximo gate: GITHUB_CLOCK_SCHEDULE_PUBLICATION_PREPARATION.
