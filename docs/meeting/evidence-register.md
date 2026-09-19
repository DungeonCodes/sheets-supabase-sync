# Evidence register — Meeting MVP

O material documental anterior deste clone registra checkpoints mais antigos. Este registro fixa os gates posteriores autorizados para a apresentação e evita regressão de status no Meeting MVP.

| Capacidade | Classificação | Evidência / gate | Número relevante |
| --- | --- | --- | --- |
| Pipeline operacional | validated | pipeline_operational_validated | current/history, idempotência e mudanças validados |
| Resiliência e governança | validated | resilience_governance_validated | retry/rollback, locks, commit ambíguo, observabilidade e alert policy |
| Multi-source | validated locally | multi_source_local_validated | 218 testes; 214 aprovados; 0 falhas; 4 pulados; 25 PostgreSQL |
| Retention/lifecycle schema | staging validated | retention_schema_staging_applied_validated | Migration 4; migrations 4/4 |
| Baseline operacional | staging validated | retention_staging_validation | 1 fonte; 6 runs; 8 eventos; 5 estados; 0 erros; 3 requests |
| Retention administrativo | staging validated | retention_staging_validation | 0 holds; 0 purge runs |
| Analytical contract | defined | analytical_contract_defined | `DIM_SOURCE`, `DIM_CATEGORY`, `FACT_CATEGORY_SCORE` |
| Analytical physical schema | in implementation | analytical_schema_environment_blocked | implementação temporariamente bloqueada pelo ambiente local |
| Analytics MVP | demonstration | meeting_mvp_demo | dataset fictício offline; não representa dados reais |
| Transformação, RBAC, BI, scheduler, E2E | planned / pending | roadmap | sem evidência de entrega ainda |

