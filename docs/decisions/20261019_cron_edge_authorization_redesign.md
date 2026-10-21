# CRON_EDGE_AUTHORIZATION_REDESIGN

Status YELLOW — preparação offline, sem implantação, 19/10/2026.
Gates automation_remote_runner_validated e probe transacional real permanecem
GREEN, sem repetição; baseline contextual 9/11/8 não foi consultado novamente.

O humano confirmou **exigir prova da origem Cron**, inclusive se uma chamada
falsa chegar depois da liberação de uma operação válida. Rejeitado wake-only
como capacidade de iniciar dispatch: saber UUID, copiar header, observar fila
ou estado de release não autentica o emissor atual. Wake público não pode
consumir nem queimar uma autorização, e foi implementado sem ledger/transport.

A fila pg_net não é fronteira de segredo. Não substituir o bearer permanente
por um token curto legível na mesma fila e declará-lo seguro. Prova de ingresso
ligada ao emissor/canal, com identidade fora da fila e dos leitores privilegiados,
é pendência concreta. Nenhum mecanismo da plataforma foi inventado para cobri-la.
O handler autenticado é biblioteca testável com verificador obrigatório injetado;
não há verificador real, listener ou caminho completo funcional aprovado.

SQL v2 preparado em schema privado novo, owner NOLOGIN sem privilégios amplos,
Edge com USAGE e três EXECUTE: claim, confirmação em transação independente e
finish sanitizado. Release/cancel só operador; trigger impede rearme. Sem RPC
pública, service_role ou acesso direto de tabela para Edge. Binding LOGIN/driver
e riscos dos grants PUBLIC da plataforma continuam sujeitos a revisão. Leitura
do probe sintético por administradores internos não aprova visibilidade de
segredos ou autorizações reais futuras.

Repo/workflow/dev fixos; PAT só Edge secret store, timeout, redirects bloqueados,
zero retries, respostas ambíguas sem compensação por novo envio. Até um fetch
por autorização sob as premissas de estado/ingresso, com possibilidade de perda.
Nada foi aplicado/criado em serviços remotos; entrypoints/DDL continuam bloqueados.

Detalhes, código, limites e testes:
[pacote de redesign](../../drafts/cron_controlled_dispatch/redesign/README.md).
Próxima aprovação: **APROVAR REVISÃO DA FRONTEIRA DE INGRESSO COM PROVA DE ORIGEM CRON**.
Isso não autoriza deploy, credenciais, job ou dispatch.
