# ADR 20260817: política conservadora de schema drift raw

## Contexto

O adaptador transacional raw já persistia estados e eventos por identidade, mas
não comparava o header da fonte com uma baseline antes da escrita. O staging
possui `schema_change_requests`, porém esse registro ainda não participava do
fluxo integrado.

## Decisão

Antes de criar `sync_run` ou aplicar transições raw, o adaptador adquire o lock
da fonte e compara o header normalizado com a baseline derivada do estado raw
atual da mesma fonte. Adição, remoção e combinações ambíguas de headers são
bloqueantes: não criam eventos, não alteram estado ou versões e registram no
máximo uma `schema_change_request` pendente idêntica.

Reorder de headers é compatível porque o leitor transforma cada linha em mapa
por nome normalizado; as colunas e valores deslocam-se juntos e o conteúdo de
negócio não é interpretado por posição. Rename não é inferido automaticamente:
é registrado como mudança estrutural genérica, exigindo revisão humana.
Headers duplicados ou inválidos continuam rejeitados pelo leitor antes da
transação.

## Consequências

A baseline transitória é derivada dos nomes das chaves dos payloads do estado
raw atual, pois as execuções prévias não tinham `schema_metadata` de header.
Uma futura evolução poderá materializar baseline aprovada em metadado próprio,
mas não altera automaticamente essa baseline nem aprova drift neste gate.

## Evidência inicial

No staging, coluna adicionada, removida e rename foram bloqueados de forma
independente antes de `sync_run` ou mutações raw. Cada diferença gerou uma
request pendente distinta; após restauração, a baseline voltou a produzir cinco
registros inalterados. Reorder e header duplicado não foram executados neste
checkpoint.
