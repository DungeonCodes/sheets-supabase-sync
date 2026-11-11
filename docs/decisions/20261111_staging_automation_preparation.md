# Preparação local da automação staging

Decisão proposta, não autorização: separar preparação dev e main em worktrees;
cron candidato minuto 17 a cada hora, opt-in estrito desligado por padrão.
Guard confere SHA no executor antes de checkout e secrets para execução agendada.
O ref dev pode mudar entre preflight e dispatch, e o próprio guard pode ser removido
por escritor de dev: revisão e proteção externas são pré-requisitos. Não se assume
monitor externo nem garantia de entrega dos ticks. Ver plano operacional em
`docs/release_staging_preparation.md` e publicação anterior em
`drafts/github-clock-recurrence/PUBLICATION_REVIEW.md`.

Revisão offline: o leitor de evidências exige clock, resumo e metadados do executor
correlacionados para classificar sucesso; modo manual legado não carrega o ID do
clock no filho e exige reconciliação externa. O gerador produz snapshots sintéticos
em fluxo, sem assumir que simula transações ou comportamento de serviços externos.

Finalizacao de seguranca: separar preflight sem environment do job staging com
`needs`; o checkout continua fixado no SHA do evento. Preflight usa variables de
repositorio/organizacao, nao do environment. Preservar manual legado significa
que o modo declarado nao autentica origem e SHA aprovado nao e exigido nele. Rejeitar
campos agendados no modo manual nao impede um chamador de omiti-los. Decisao humana
sobre contrato manual ou controles externos efetivos permanece pendente; proteger
dev e o environment e condicao anterior ao piloto recorrente.

Contrato posterior decidido: exigir SHA aprovado e autorizacao temporaria por numero
de run em todos os modos, inclusive scheduled, com reruns bloqueados. Manual legado
quebra intencionalmente. O numero e publico e disputavel, nao prova identidade;
aprovacao externa e governanca sao necessarias. Os inputs de clock nao comprovam
origem; a recorrencia autonoma nao atende ao contrato por run atual.

Escopo final do checkpoint A: executor manual protegido; modo scheduled falha.
Modo manual nao prova origem humana: outros dispatches podem disputar o numero
de run autorizado. Clock main fica separado e sem modificacao.
