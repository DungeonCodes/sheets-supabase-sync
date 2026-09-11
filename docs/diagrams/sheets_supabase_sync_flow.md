# Fluxo executivo — sheets-supabase-sync

Backup editável em Mermaid do fluxograma principal. O arquivo fonte para a
reunião é `sheets_supabase_sync_flow.drawio`.

```mermaid
flowchart LR
  subgraph CURRENT["A. VALIDADO / IMPLEMENTADO — fixtures fictícias; não representa produção"]
    direction LR
    A["ORIGEM<br/>Google Forms → Google Sheets"]
    B["INGESTÃO<br/>Service Account read-only<br/>GoogleSheetsReader"]
    C["PREPARAÇÃO<br/>Snapshot<br/>Normalização + validação<br/>Business key + row hash"]
    D["COMPARAÇÃO<br/>Recebido × estado atual<br/>Diff por fonte/chave"]
    E["MUDANÇAS<br/>INSERT • UPDATE<br/>TOMBSTONE • RESTORE"]
    F["PERSISTÊNCIA<br/>Transação psycopg<br/>Supabase / PostgreSQL"]
    G["ESTADO RAW<br/>raw_import_rows<br/>raw_current_rows<br/>sync_runs"]
    A --> B --> C --> D --> E --> F --> G
  end

  subgraph FUTURE["B. PRÓXIMA CAMADA / EVOLUÇÃO — PLANEJADO / PRÓXIMA ETAPA"]
    direction LR
    H["TRANSFORMAÇÃO ANALÍTICA<br/>Idempotente e minimizada<br/>Origem: raw_current_rows"]
    I["STAR SCHEMA<br/>DIM_SOURCE • DIM_CATEGORY<br/>FACT_CATEGORY_SCORE"]
    J["DASHBOARD / BI<br/>Somente dados curados<br/>Acesso mínimo + RLS/RBAC"]
    H -.-> I -.-> J
  end

  G -. próxima etapa .-> H

  subgraph CONTROLS["CONTROLES DE SEGURANÇA E RESILIÊNCIA"]
    direction LR
    K["Acesso e isolamento<br/>Google read-only • fonte isolada<br/>business key • lifecycle/enabled"]
    L["Qualidade<br/>schema drift bloqueante<br/>sem mudança destrutiva<br/>último estado válido"]
    M["Concorrência e falhas<br/>advisory/source lock<br/>retry • rollback<br/>commit ambíguo → reconciliação"]
    N["Ambiente e operação<br/>staging guard • produção bloqueada<br/>logs sanitizados<br/>falha isolada por fonte"]
  end

  classDef validated fill:#E3FCEF,stroke:#36B37E,color:#164B35,stroke-width:2px;
  classDef planned fill:#DEEBFF,stroke:#4C9AFF,color:#0747A6,stroke-width:2px,stroke-dasharray:6 4;
  classDef control fill:#F4F5F7,stroke:#A5ADBA,color:#172B4D;
  class A,B,C,D,E,F,G validated;
  class H,I,J planned;
  class K,L,M,N control;
```

Legenda:

- **VALIDADO:** evidência documentada com fixtures fictícias; não significa produção.
- **EM IMPLEMENTAÇÃO:** trabalho iniciado, ainda sem gate de validação completo.
- **PLANEJADO:** contrato/desenho aprovado, implementação ainda pendente.

Fontes: `docs/architecture.md`, `docs/workflow.md`,
`docs/activity-3/implementation-plan.md`,
`docs/decisions/20260806_inicie_etl_clientes_orientacao.md`,
`docs/roadmap.md`, `docs/decisions/20260819_operational_retry_policy.md`,
`docs/decisions/20260902_lifecycle_aware_code_rollout.md` e
`docs/decisions/20260903_minimum_analytical_contract.md`.
