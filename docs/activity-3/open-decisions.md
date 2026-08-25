# Decisões pendentes da Atividade 3

Estas perguntas exigem resposta da empresa, de Eric ou de responsáveis formalmente designados. A auditoria não presume respostas. “Decisor proposto” é apenas a área que precisa ser confirmada.

| ID | Pergunta pendente | Por que é necessária | Decisor proposto | Necessária antes de | Status |
| --- | --- | --- | --- | --- | --- |
| OD-01 | Qual frequência de atualização é esperada por cliente? | Define scheduler, quota e custo. | Eric / Operações | Fase 1 e COST-01 | pendente |
| OD-02 | Qual volume médio e máximo de linhas, colunas, planilhas e histórico? | Dimensiona ingestão, raw, benchmark e custo. | Operações / clientes | Fases 2 e 4 | pendente |
| OD-03 | Qual tempo máximo aceitável entre alteração e dashboard atualizado? | Define SLA, batch versus quase tempo real e alerta de atraso. | Diretoria de Operações | Fase 1 | pendente |
| OD-04 | Qual ferramenta de BI é preferida ou já homologada? | Define conector, segurança, free tier e dashboard. | Diretoria / TI | Fase 5 | pendente |
| OD-05 | Há necessidade comprovada de quase tempo real? | Pode mudar arquitetura, quota, custo e contingência. | Operações | antes de qualquer arquitetura de eventos | pendente |
| OD-06 | Quantos usuários por cliente e quais escopos/hierarquias de acesso existem? | Define identidade, RLS/RBAC e testes negativos. | Operações / Segurança | Fase 5 | pendente |
| OD-07 | Há necessidade de anonimização ou pseudonimização e quais campos são pessoais/sensíveis? | Define staging, modelo, BI e controles LGPD. | DPO / Segurança / negócio | Fases 2 e 4 | pendente |
| OD-08 | Quais prazos definitivos e janela técnica de reconciliação valem para raw, runs, logs, erros, requests e artefatos? | Define custo, descarte, auditoria e configuração por fonte; os valores atuais são apenas recomendações técnicas. | DPO / Segurança / Operações | migration de retenção e piloto | pendente |
| OD-09 | Quais bases legais, direitos do titular, critérios de legal hold e procedimentos de descarte/incident response se aplicam? | Evita tratar LGPD ou hold como requisito apenas técnico. | DPO / Jurídico | piloto com qualquer dado de cliente | pendente |
| OD-10 | Qual orçamento aceitável após o free tier e qual limite mensal rígido? | Permite cenários de custo, pay-as-you-go e gatilhos. | Diretoria / Financeiro | Fase 7 | pendente |
| OD-11 | Quem é responsável por onboarding, compartilhamento, reconciliação, offboarding e aceite da migração? | Define responsabilidades, revogação de credenciais e evidência final. | Operações / Eric | Fase 7 e primeiro cliente | pendente |
| OD-12 | Qual canal de alertas deve ser usado e quem recebe cada severidade? | Define e-mail, escalonamento, deduplicação e suporte. | Operações | Fase 6 | pendente |
| OD-13 | Qual prazo de recuperação (RTO) e perda máxima aceitável (RPO)? | Define último dado válido, backup e restauração. | Operações / TI | Fases 2 e 6 | pendente |
| OD-14 | Quem cria, armazena, rotaciona e revoga credenciais Google/Supabase/BI? | Define cofre, mínimo privilégio e resposta a incidente. | Segurança / TI | Fase 1 | pendente |
| OD-15 | É necessário backup externo ao provedor? Com qual retenção, legal hold e teste de restore? | Define contingência e deixa claro que purge no banco não elimina automaticamente backups. | TI / Segurança / Diretoria | Fase 7 e antes de purge | pendente |
| OD-16 | Quem pode aprovar policy, ativar/liberar hold, autorizar purge e concluir offboarding? | O desenho separa sincronizador, aprovador e executor; a operação destrutiva exige owner formal. | DPO / Segurança / Operações | migration de retenção e produção | pendente |

## Regra de decisão

Cada resposta aprovada deve registrar data, decisor, alcance e impacto. Se for durável e técnica, deve gerar ou atualizar uma ADR; se for operacional, deve atualizar plano, runbook, riscos, critérios de aceite e rastreabilidade. Resposta informal não muda requisito para `validated`.
