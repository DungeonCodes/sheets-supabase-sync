# sheets-supabase-sync | Fluxo operacional proposto

> **PROPOSTA PARA VALIDAÇÃO COM A INICIE** — não é fluxo definitivo de produto.

Fallback Mermaid do arquivo editável `sheets_supabase_sync_operational_flow.drawio`.

```mermaid
flowchart TB
  subgraph CLIENT["CLIENTE DA INICIE"]
    C1["1. Form / Sheet existente"] --> C2["2. Compartilha Sheet<br/>e envia URL"]
    C10["10. Consome dashboard<br/>sem administrar banco"]
  end

  subgraph INICIE["INICIE"]
    I3["3. Cadastra nova fonte<br/>operação assistida no MVP"] --> I4["4. Configura a fonte<br/>nome • aba • business key<br/>campos • periodicidade"]
    I6["6. Aprova ativação<br/>e mudanças de schema"]
    I9["9. Configura o BI<br/>somente sobre dados curados"]
  end

  subgraph APP["APLICAÇÃO / PIPELINE"]
    A5["5. Valida a fonte<br/>URL • leitura • aba • headers"]
    PII["PII / campos permitidos<br/>decisão pendente"]
    A7["7. Fonte ativada<br/>após validação e aprovação"]
    A8["8. Sincronização automática<br/>lê • valida mudanças • persiste<br/>Detalhamento: sheets_supabase_sync_flow.drawio"]
    SCHED["Agendamento regular<br/>FUTURO"]
  end

  subgraph PLATFORM["GOOGLE / SUPABASE"]
    G["Google Sheets<br/>somente leitura"]
    RAW["Supabase — RAW / OPERACIONAL<br/>interno • não exposto ao cliente<br/>Looker não consulta raw"]
    CURATED["ANALYTICS / CURADO<br/>somente dados necessários<br/>acesso mínimo para BI"]
  end

  subgraph BI["BI / CONSUMO"]
    L["Looker Studio / BI<br/>somente leitura<br/>ferramenta a validar"]
  end

  C2 --> I3
  I4 --> A5
  A5 -. "PII: aprovação" .-> PII
  A5 --> I6 --> A7 --> A8
  G -->|leitura| A8
  A8 -->|estado interno| RAW
  RAW -. "transformação planejada" .-> CURATED
  CURATED -.-> I9 -.-> L -.-> C10
  A8 -.-> SCHED

  subgraph MVP["MVP SUGERIDO — menos automação inicial"]
    M1["CLIENTE<br/>envia URL"] --> M2["INICIE<br/>configura fonte"] --> M3["SISTEMA<br/>valida + sincroniza"] --> M4["INICIE<br/>conecta BI"] --> M5["CLIENTE<br/>consome dashboard"]
  end

  subgraph SELF["FUTURO — SELF-SERVICE"]
    S1["Cliente cadastra URL"] -.-> S2["Sistema valida"] -.-> S3["Sistema provisiona fonte"] -.-> S4["Sistema agenda sync"] -.-> S5["Sistema libera BI controlado"]
  end

  subgraph DECISIONS["DECISÕES PARA VALIDAR COM A INICIE"]
    D1["Quem cadastra a URL?<br/>Cliente ou Inicie?"]
    D2["Quem escolhe a business key?"]
    D3["Quem aprova mudanças de schema?"]
    D4["Qual periodicidade?"]
    D5["Quem configura o Looker?"]
    D6["Cliente terá acesso técnico ao Supabase?"]
    D7["Qual nível de self-service?"]
    D8["Quem recebe alertas?"]
    D9["Como será o onboarding institucional?"]
    D10["Quem aprova PII e campos permitidos?"]
  end

  classDef validated fill:#E3FCEF,stroke:#36B37E,color:#164B35;
  classDef proposal fill:#DEEBFF,stroke:#4C9AFF,color:#0747A6;
  classDef pending fill:#FFF0B3,stroke:#FFAB00,color:#614700;
  classDef future fill:#EAE6FF,stroke:#6554C0,color:#403294,stroke-dasharray:6 4;
  class G,A5,RAW validated;
  class C1,C2,I3,I4,A7,A8,M1,M2,M3,M4,M5 proposal;
  class I6,PII,D1,D2,D3,D4,D5,D6,D7,D8,D9,D10 pending;
  class I9,C10,CURATED,L,SCHED,S1,S2,S3,S4,S5 future;
```

## Legenda

- **VALIDADO TECNICAMENTE:** comprovado no alcance documentado e com fixtures.
- **PROPOSTA OPERACIONAL:** forma sugerida de operar, ainda sujeita à Inicie.
- **DECISÃO PENDENTE:** responsabilidade ou regra ainda não definida.
- **FUTURO:** automação, analytics ou BI ainda não implementados.

O acesso proposto preserva a separação: o raw é interno, o cliente não recebe
`service_role` nem chave Supabase e o BI consome apenas a camada analítica
curada com acesso mínimo.
