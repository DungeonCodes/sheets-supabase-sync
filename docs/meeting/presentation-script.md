# Roteiro prático — 7 a 10 minutos

## 0:00–1:00 · Problema e objetivo

- **Mostrar:** hero.
- “Planilhas são úteis para registrar informação, mas não para sustentar um processo auditável. Construímos um pipeline que preserva o último estado válido e prepara o dado para analytics.”
- Pipeline operacional validado; analytics/BI é a próxima camada.

## 1:00–2:00 · Arquitetura

- **Mostrar:** arquitetura.
- Sheets read-only → Python → validação/diff → Supabase/PostgreSQL → analytics/BI.
- Até current/history e controles: validado. Contrato analytics: definido.

## 2:00–3:30 · Pipeline já validado

- **Mostrar:** capacidades e resultados.
- Idempotência, mudanças, schema drift, current/history.
- Destacar: **218 testes**, **214 aprovados**, **0 falhas**, **25 PostgreSQL**, **4/4 migrations**.

## 3:30–4:30 · Resiliência e segurança

- **Mostrar:** fluxos e governança.
- Falha → rollback → retry controlado → último estado válido.
- Schema inesperado → bloqueio → revisão → sem publicação incorreta.
- Read-only, privilégios mínimos, RLS, raw separado de analytics, retention/lifecycle.

## 4:30–5:30 · Multi-source

- **Mostrar:** Fonte A e Fonte B.
- Schemas, locks e falhas independentes; mesma chave lógica pode existir nas duas.
- Limite: validação local, não operação produtiva ou scheduler persistente.

## 5:30–7:30 · Analytics fictício

- **Mostrar:** badge “DADOS FICTÍCIOS DE DEMONSTRAÇÃO”.
- Alternar Todas → Fonte 01 → Fonte 02.
- “É assim que a camada analítica deverá chegar ao consumidor final.”
- Os KPIs são sintéticos; não vieram do pipeline real.

## 7:30–8:30 · Roadmap e encerramento

- Validado: pipeline, resiliência, observabilidade, retention/lifecycle, multi-source e contrato analítico.
- Em andamento: analytics schema. Próximos: transformation, RBAC, BI, scheduler e E2E.
- **Encerrar:** “O pipeline operacional está validado. A próxima etapa é materializar analytics/BI; a automação completa vem depois.”

## 8:30–10:00 · Margem

- Perguntas, transições ou repetição breve do filtro.

