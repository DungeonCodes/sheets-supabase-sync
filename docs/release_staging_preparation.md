# Release staging — plano para revisão, não autorização

IMPLEMENTADO LOCALMENTE: CLI, executor, candidato de clock em worktree separado e
instrumentos offline. TESTADO OFFLINE: consultar run log. VALIDADO REMOTAMENTE:
apenas evidências históricas documentadas em `drafts/github-clock-recurrence/`;
nenhuma validação hospedada do diff atual. PENDENTE DE PUBLICAÇÃO: todos os diffs
atuais. PENDENTE DE APROVAÇÃO ERIC: dimensionamento, cadência, SLA e responsável.
Não há declaração de prontidão de produção.

## Regras comuns e governança

Todas as operações remotas abaixo são futuras, exigem autorização específica e
devem registrar aprovador, janela, SHA, execução e decisão. Não publicar arquivos de
preparação por acidente: checkpoint A limita-se ao CLI, executor e regressões
necessárias; checkpoint C limita-se ao clock. `drafts/`, dados sintéticos e este
plano são documentação/revisão, não workflows a publicar. Refazer `git ls-remote`
e `git status` antes de cada mudança; interromper se a base for diferente da
revisada, sem integrar automaticamente. Definir aprovadores humanos para arquivos
de workflow e código executado, desabilitar bypass quando viável, exigir revisão
independente e checks, restringir escrita e alterações de regras; avaliar CODEOWNERS
com nomes reais somente após responsáveis serem designados. CODEOWNERS sozinho não
impõe revisão sem proteção/rulesets. Restringir quem pode alterar SHA aprovado,
variables, environment e secrets. Auditoria de acesso a staging e conteúdo dos logs
públicos é requisito; nenhum acesso a dados pessoais ou segredos no relatório.

Clock em main e executor em dev separam responsabilidades, mas o guard reside na
própria dev: um escritor pode removê-lo. `workflow_dispatch` em `dev` não oferece
fixação atômica do código do workflow após o preflight. Congelar/revisar dev e
aprovar o SHA completo que já contenha o guard; variável é snapshot e não revoga
jobs iniciados. Guard não substitui proteção Git ou aprovação de environment.
O guard de SHA aprovado é obrigatório para o modo scheduled; o modo manual legado
continua disponível com seus próprios controles. Clock e dispatch não fazem retry
automático, mas políticas internas pré-existentes dos conectores/core permanecem.

## A — publicação do patch e executor em dev

Pré-requisitos: bases remotas renovadas; revisão de `src/sheets_supabase_sync/batch_cli.py`,
`.github/workflows/scheduled-sync.yml` e `tests/unit/test_dispatcher.py`; governança
de dev aprovada; staging sem recorrência ativa. Base preparada `4e18a97`, conferir
ref atual; o SHA aprovado para recorrência será o commit final revisado, não esta base.
Comandos de revisão, somente leitura: `git diff -- src/sheets_supabase_sync/batch_cli.py
.github/workflows/scheduled-sync.yml tests/unit/test_dispatcher.py`, `git diff --check`;
executar `python -m unittest discover -s tests` e testes candidatos Node/Python.
Publicação por processo de revisão autorizado; nenhum comando de escrita é autorizado
por este documento. Efeito esperado: falha parcial retorna 1 e guard antecede checkout
e credenciais. Risco: quebra de contrato manual ou acesso indevido. GREEN: diff exato,
checks aprovados, revisão e SHA registrado; RED: falha, divergência ou segredo exposto.
Rollback: parar recorrência, reconciliar jobs e reverter código por revisão; executor
anterior não possui guard. Evidências: diff, checks, aprovações e SHA. Aprovação:
publicação específica por responsável da dev.

## B — validação remota controlada do executor

Pré-requisitos: A concluído, staging guard e acesso revisados, janela e fonte fictícia
autorizadas, opt-in recorrente desligado, operador e rollback definidos. Base: SHA
final de A. Comandos de inspeção sugeridos `gh run view RUN_ID` e
`gh api repos/OWNER/REPO/actions/runs/RUN_ID` após substituir IDs revistos; não
imprimir logs brutos ou credenciais. O dispatch e qualquer sincronização exigem
autorização própria, com escopo exato; nenhuma está concedida aqui. Verificar guard,
checkout SHA, resumo, código de saída e reconciliação staging por leitura autorizada.
Efeito: no máximo execução controlada autorizada; riscos: credenciais, corrida,
escrita e logs públicos. GREEN: evidências consistentes, sem fonte falha e guard
comprovado; RED: resultado ambíguo, mismatch, falha ou exposição. Parar sem retry;
reconciliar antes de qualquer decisão. Rollback: interromper nova execução e manter
opt-in off, sem apagar dados; ações transacionais em andamento exigem análise.
Evidências: IDs, SHA e agregados sanitizados. Aprovação: execução staging específica.

## C — publicação do clock em main com opt-in desativado

Pré-requisitos: A e B GREEN, governança e revisão de `.github/workflows/staging-clock.yml`;
base preparada `80cdde4`, revalidar. Diff somente clock no worktree de main;
`git diff -- .github/workflows/staging-clock.yml`, `git diff --check`, actionlint e
testes de manual/schedule. Cron `17 * * * *` significa minuto 17 de cada hora UTC,
é proposta, não autorização de ativação. Mesmo com opt-in ausente o cron cria runs
que bloqueiam antes do POST; publicação do cron também exige autorização específica.
Efeito: workflow fica publicado, agendamentos podem iniciar, sem dispatch autorizado.
Riscos: consumo de runner, logs, configuração pré-existente de variável e drift.
GREEN: opt-in comprovadamente off, diff e controles aprovados; RED: variável true,
SHA não revisado, alteração inesperada ou falha de guard. Rollback: manter opt-in
off e restaurar clock anterior por revisão; checar execuções em andamento. Evidências:
diff, SHA main, valores/estado sanitizados e revisão. Aprovação: publicação específica.

## D — validação hospedada do relógio

Pré-requisitos: C concluído, janela e acionamento explícitos, opt-in off, titular de
revisão e executor aprovado. Inspeção `gh run view RUN_ID` e API de metadados após
autorização; testar bloqueio e, somente com autorização separada para dispatch, modo
manual e identidade do filho. Não acionar Actions por este plano. Efeito esperado:
confirmar bloqueio e comportamento real; risco de dispatch e concorrência GitHub.
GREEN: evidência de bloqueio e testes autorizados consistentes; RED: dispatch não
autorizado, segredo ou ambiguidade. Parar, manter opt-in off e reconciliar cada ID;
não repetir POST incerto. Rollback: reverter clock conforme C. Evidências: IDs,
SHA, status e logs sanitizados. Aprovação: execução hospedada específica.

## E — piloto recorrente supervisionado

Pré-requisitos: A–D GREEN; cadência, tolerância, janela, orçamento, dono, acesso,
SHA final de dev e verificação independente aprovados. Apenas após autorização
específica configurar SHA e opt-in; inspeção sugerida `gh variable list` sem imprimir
segredos e `gh run list --workflow staging-clock.yml --branch main`. Efeito: ticks
horários podem disparar staging. Riscos: atraso/perda de tick, quota, corrida,
credenciais e processos já iniciados. GREEN: primeiro tick e filho reconciliados,
sem fonte falha; RED: guard, falha parcial, silêncio ou evidência inconsistente.
Rollback: desabilitar opt-in, verificar jobs já iniciados e reconciliar; snapshot de
variable não revoga job ativo, não cancelar transação cegamente. Evidências: janela,
aprovação, SHA, IDs e agregados. Aprovação: ativação temporária específica.

## F — monitoramento, reconciliação e encerramento

Pré-requisitos: piloto autorizado e responsável independente ativo. Verificar
periodicamente workflow, último tick, executor, falhas, busy e última evidência válida;
`node drafts/github-clock-recurrence/inspect-evidence.mjs < evidencias.json` lê apenas
arquivo local sanitizado. Uma agenda independente precisa fornecer horários esperados;
ausência de dados do próprio clock não comprova tick perdido. Reconciliar manualmente
o estado staging autorizado, sem expor linhas. GREEN: evidências completas, custos e
resultados aprovados; RED: silêncio, falha ou ausência de reconciliação: suspender e
investigar. Encerramento: opt-in off, confirmar jobs e decisão humana; rollback como
E, sem apagar histórico. Evidências: IDs, resumo sanitizado, intervalos e decisão.
Aprovação: encerramento/continuidade e quaisquer mudanças remotas específicas.
