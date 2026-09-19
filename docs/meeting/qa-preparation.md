# Perguntas prováveis — Meeting MVP

## O que já está realmente funcionando?
O pipeline operacional foi validado: leitura read-only, current/history, idempotência, mudanças, schema drift, resiliência, governança e multi-source local. O analytics visual é fictício.

## O que ainda é mock?
KPIs, gráficos e tabela do Analytics MVP usam dataset sintético embutido no HTML. Eles demonstram a experiência prevista para o consumidor final.

## Por que Supabase?
Ele fornece PostgreSQL e controles como RLS adequados à PoC. A demo não depende do serviço para funcionar.

## Por que Python?
Ele concentra leitura, validação, diff e orquestração em código testável e auditável.

## O que acontece se a planilha mudar?
Schema inesperado é bloqueado antes de publicar e segue para revisão.

## O que acontece se uma sincronização falhar?
Há rollback, retry somente quando seguro e preservação do último estado válido. Resultado ambíguo não recebe retry cego.

## Como múltiplas planilhas são isoladas?
Cada fonte mantém schema, current/history, lock e falha isolados. A prova local confirmou continuidade quando uma fonte falha.

## Como LGPD foi considerada?
Leitura mínima, privilégios mínimos, RLS, separação raw/analytics e retention/lifecycle. Decisão jurídica final e executor de purge seguem futuros.

## Onde entra o Star Schema?
O contrato `DIM_SOURCE`, `DIM_CATEGORY` e `FACT_CATEGORY_SCORE` organiza dados para BI. O schema físico está em implementação.

## O que falta para operação automática?
Analytics físico, transformação, RBAC, BI, scheduler/runtime, executor de purge e E2E final.

