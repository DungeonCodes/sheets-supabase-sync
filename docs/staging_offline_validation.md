# Validação offline e limites

Os 30 skips da suíte Python são intencionais neste gate e não são PASS:

| Quantidade | Grupo | Classificação e cobertura pendente |
| ---: | --- | --- |
| 23 | PostgreSQL/Supabase local: multi-source, repositório raw e retenção | Ambiente indisponível; faltam verificações reais de locks, transações, idempotência, constraints e retenção. |
| 2 | PostgreSQL operacional | Ambiente indisponível; faltam rollback e concorrência com banco real. |
| 3 | Fluxo E2E e integração Supabase | Dependência externa/local indisponível; requer Supabase e psql, e alguns casos aplicam SQL, proibido neste gate. |
| 1 | Google Sheets | Dependência externa e fixture privada fictícia; execução exige autorização humana. |
| 1 | Performance | Opcional e lento; skip intencional, não é evidência de escala. |

Testes em memória e mocks não substituem esses testes. O actionlint de release
oficial v1.7.12 foi usado em diretório temporário após verificação de attestation
GitHub, sem dependência de produção; consultar run log para resultado. PyYAML e
actionlint são análises locais, não demonstram comportamento do scheduler hospedado.

Monitor local não é monitor independente. `EVIDENCE.md` define entrada, limites,
falha fechada e correlação de execuções. Gerador só cria snapshots sintéticos e não
executa testes de integração nem benchmarks. Não versionar dados gerados ou arquivos
locais de evidência. Releases e integração permanecem sujeitos a autorização.
