# Checkpoint A — pacote para revisão, não publicado

Base: `4e18a977fef7f9b00211cbc0a1da235ad368b395` (dev); revalidar antes de publicar.
O patch `checkpoint-a.patch` contém exatamente estes cinco caminhos:

1. `src/sheets_supabase_sync/batch_cli.py` — exit 1 após resumo quando há fonte falha.
2. `.github/workflows/scheduled-sync.yml` — guard, checkout fixo e resumo agregado.
3. `tests/unit/test_dispatcher.py` — regressões de falha parcial, no_changes e busy.
4. `tests/unit/test_staging_executor_summary.py` — adapter real e sanitização.
5. `tests/cron_dispatch/staging-executor.test.mjs` — guard real e ordem das etapas.

Gerado sem staging e conferido com `git apply --cached --check` contra o índice
limpo e `git apply --reverse --check` contra o estado local. Os testes novos estão
untracked; `git diff` sozinho não os inclui. O patch é artefato de revisão local,
não um sexto arquivo do pacote. Não incluir clock main, demais drafts, dados,
monitoramento, escala, documentação ou alterações locais não listadas.

## Compatibilidade e variáveis

Escopo: executor staging manual protegido. Manual legado quebra intencionalmente:
exige SHA aprovado, autorização por número de run e validade curta. Sem as novas
variables a execução falha fechada. O log público é agregado e falhas parciais falham.
O modo `scheduled` é sempre bloqueado, independentemente de variables ou inputs.
As variables ficam no repositório (ou organização), fora do environment staging:

* `STAGING_CLOCK_APPROVED_DEV_SHA`: SHA completo aprovado por humano; `github.sha`
  e `github.workflow_sha` devem coincidir com ele.
* `STAGING_DISPATCH_AUTHORIZED_RUN_NUMBER`: um único número de run do executor.
* `STAGING_DISPATCH_APPROVAL_EXPIRES_AT`: UTC ISO com segundos ou milissegundos,
  futuro e no máximo 15 minutos no momento do preflight.

Número e validade são exigidos no caminho manual; `scheduled` não é aceito. Cada
tentativa deve ser run_attempt 1; reruns são bloqueados.
Dispatch verifica novamente expiração antes do checkout, inclusive após aprovação
de environment. Após uso, operador autorizado deve revogar/remover as variables de
run e validade e registrar resultado; nunca rearmar o mesmo número. Nenhuma escrita
de variables é feita pelo workflow. Um número já consumido não se aplica à próxima
run e o rerun é bloqueado, mas não há consumo atômico, revogação instantânea de jobs
já iniciados nem garantia de identidade de quem obteve aquele número. Outra pessoa
com permissão de dispatch pode disputar o número previsto; revisão independente do
environment e controle dos autores devem prevenir a corrida. Não tratar o número como
segredo ou prova de origem. Configuração remota exige autorização própria.
O job `preflight` não usa environment nem secrets de dados e declara permissões
vazias. `dispatch` exige `needs: preflight`, usa `environment: staging`, recebe
`contents: read`, fixa e verifica o SHA antes de materializar secrets. O token
automático do GitHub ainda existe por job. O staging guard acontece após materialização
e antes do dispatcher. GitHub avalia regras do environment antes de iniciar o job;
um preflight reprovado não libera o job dependente. Confirmar em teste hospedado.
Como preflight não usa environment, suas variables devem estar em repositório ou
organização; variables apenas de staging são invisíveis. Uma alteração de variable
entre jobs não é revogação atômica: no piloto congelar revisão e controlar alterações.

Modo é input declarado pelo chamador, não identidade autenticada. O clock manual
atualmente publicado em main dispara sem esses inputs e poderá ser bloqueado pelo
novo contrato: seu executor não terá SHA e autorização por run automaticamente.
Também é possível que o clock ou outro chamador consuma uma autorização reservada
se disparar com aparência manual e alcançar o run_number correspondente. Antes de
armar uma autorização, suspender/impedir operacionalmente outros dispatches com
autorização específica e confirmar que não há runs pendentes; o código não prova
que a origem seja humana nem garante exactly-once. O GitHub fornece evento e ator,
mas os mecanismos atuais não provam que o clock específico iniciou o dispatch.
A recorrência fica separada e não está pronta para ativação. O próprio
código do guard pode ser modificado por escritor de dev. O SHA
efetivo é comparado antes do checkout quando o guard permanece íntegro, mas o
workflow_dispatch por branch móvel não fixa atomicamente o workflow entre GET e POST.
Esses limites e a ausência de governança bloqueiam o piloto recorrente.

## Governança observada read-only

`dev` e `main` não têm proteção; rulesets do repositório e regras efetivas retornaram
vazios. Um colaborador listado com papel admin; a lista não garante inventário de
acessos herdados/organização. Nenhuma revisão de PR obrigatória foi identificada.
Environment staging possui política de branch customizada `dev`, sem aprovadores
retornados; isso restringe implantação, não protege o código de dev. Actions permite
todas as actions e não exige pin em SHA. Permissão padrão é read; workflow declara
contents read. CODEOWNERS não encontrado nos três locais suportados na dev.
Exigir regras/rulesets para dev, revisão independente e CODEOWNERS aplicado por
regras, responsáveis por workflow e executor, controles de bypass, acesso a secrets
e aprovação do SHA, com auditoria antes do piloto. Não configurar remotamente aqui.
No estado consultado, abrir PR ou fazer merge não exige tecnicamente alterar regras,
mas revisão independente não é imposta pelo GitHub. Para torná-la obrigatória é
necessário configurar e verificar proteção/ruleset; disponibilidade de revisor
independente não foi confirmada. Aprovação de PR e merge são atos separados do PR.

## Validação e publicação futura

Revisar patch e resultados; abrir branch de preparação a partir de dev atual e PR
para dev somente após autorização de commit/push/PR. Reavaliar base antes de aplicar.
O `ci.yml` possui triggers push e pull_request, portanto push/PR pode disparar Actions;
a autorização futura deve tratar explicitamente esse efeito. Abrir PR não autoriza
merge nem dispatch/sincronização; o executor só declara workflow_dispatch. O CI atual
não referencia staging nem secrets de dados e não invoca dispatcher; instala pacotes
via rede e executa código e testes do checkout com token padrão de leitura. Código ou
workflow de CI alterados num PR podem mudar essa análise; revisar seu diff e acesso.
CI Python não executa os testes Node; executá-los como check adicional autorizado.
Revisão hospedada do executor, apenas com autorização específica posterior: confirmar
SHA final, staging guard, opt-in off, compatibilidade manual, resumo e reconciliação
com dados fictícios aprovados; não repetir POST ambíguo. Não publicar clock neste gate.

Rollback futuro: manter opt-in off; identificar jobs existentes e reconciliar antes
de agir. Reverter por PR o commit exato isolado do pacote A (`git revert <SHA_DO_COMMIT_A>`
em branch própria, após autorização), revisando o diff antes do merge. Se houver
commits dependentes ou merge commit, selecionar o procedimento de revert apropriado
após inspeção humana; não executar cegamente. A revisão anterior não tem guard SHA.
Não apagar histórico, dados ou evidências; execução de rollback remoto também requer
autorização. Nenhum rollback foi executado nesta revisão.

## Estado da finalização de segurança

Escopo manual preparado para revisão Git. Origem não é autenticada, sequência de
runs pode ser disputada, governança e validação hospedada permanecem pendentes.
O piloto recorrente não está autorizado. Nenhuma alteração remota ou execução
hospedada foi efetuada.

## Sequência Git futura — não executar neste gate

Após revisão do novo contrato e autorização explícita abrangendo também a CI automática,
revalidar `git ls-remote origin refs/heads/dev` e preservar o checkout atual. Criar
worktree limpo e branch de preparação com
`git worktree add -b prepare/checkpoint-a <WORKTREE_NOVO> <BASE_DEV_REVISADA>`.
Nesse worktree, executar `git apply --index <PATCH_REVISADO>`, inspecionar
`git diff --cached --check` e `git diff --cached`, confirmar os cinco arquivos,
executar testes Python e Node e actionlint. Somente se aprovado, executar commit
e `git push -u origin prepare/checkpoint-a`, depois `gh pr create --base dev` com
descrição do diff e limites do guard. Push e PR podem criar runs de CI. Não fazer
merge, despacho manual ou sincronização sem outra autorização. Revalidar o SHA após
revisão; o SHA aprovado para dispatch manual será o commit final em dev, não a base.

Patches anteriores são históricos e não devem ser publicados. O patch atual precisa
de revisão; testes estáticos não provam sequenciamento no GitHub hospedado.
