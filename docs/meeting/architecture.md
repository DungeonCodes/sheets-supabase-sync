# Arquitetura para a reunião

```text
Google Sheets          Python Synchronizer          PostgreSQL / Supabase
(read-only)      →      validation + diff      →    current state + event history
                                                              │
                                                              ▼
                                              analytical contract → analytics → BI
```

## Estado das camadas

- **Validado:** Google Sheets read-only; current state e event history; idempotência; insert/update/tombstone/restore; reorder neutro; schema drift; retry/rollback PostgreSQL; advisory lock; reconciliação de commit ambíguo; observabilidade e alert policy.
- **Aplicado e validado em staging:** Migration 4 de retention/lifecycle, com legal hold estrutural, evidência de purge, state machine, RLS, grants, guards, proteção de DELETE/TRUNCATE e serialização administrativa.
- **Validado localmente:** duas fontes fictícias com schemas diferentes, mesma business key em fontes distintas, isolamento de current/history, lock, rollback, retry, lifecycle e batch sequencial após falha.
- **Definido / em implementação:** contrato analítico `DIM_SOURCE`, `DIM_CATEGORY` e `FACT_CATEGORY_SCORE`; schema físico bloqueado temporariamente pelo ambiente local.
- **Planejado:** transformação, RBAC analítico, BI real, scheduler/runtime e E2E final.
- **Demonstração:** dashboard analytics offline com dados sintéticos.

A camada analítica separa os dados técnicos/raw dos dados preparados para BI. O contrato está definido; o schema físico ainda não está aplicado.

