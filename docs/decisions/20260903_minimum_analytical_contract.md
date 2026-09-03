# Contrato analitico minimo para a Atividade 3

**Data:** 2026-09-03

## Status e alcance

Contrato definido para a entrega; objetos e transformacao ainda nao foram
implementados. O caso usa somente dados ficticios ja versionados. Nao aprova
dados reais, producao, nova migration, SQL, BI, RLS, scheduler ou acesso
externo.

## Requisitos oficiais e prioridade de entrega

A fonte oficial exige ETL/ELT robusto, armazenamento analitico, modelo
dimensional Star Schema ou Snowflake, fatos, dimensoes, consultas de BI,
controle RLS/RBAC, desempenho, protecao LGPD e representacao no Draw.io. Ela
nao define um dominio de cliente, metricas, hierarquia, volume, SLA ou
ferramenta de BI.

| Prioridade | Requisitos oficiais | Recorte desta decisao |
| --- | --- | --- |
| `MUST_HAVE` | `OBJ-01`, `OBJ-02`, `OBJ-03`, `DQ-03`, `STORE-01`, `STORE-03`, `STORE-04`, `WF-04`, `WF-05`, `WF-06` | fluxo raw para analytics para BI; banco e modelo escolhidos; uma fato, dimensoes e metricas; minimizacao; contrato de acesso |
| `SHOULD_HAVE` | `DQ-01`, `DQ-02`, `PROC-01`, `PROC-05`, `STORE-02`, `WF-01`, `WF-03`, `WF-08`, `AVAIL-01` | consulta local medida, SQL simples/portavel, lineage, ultimo conjunto analitico valido e desenho coerente com o fluxo completo |
| `FUTURE_PRODUCTION` | `COST-01` a `COST-03`, `CLIENT-02`, `CLIENT-03`, `TECH-01`, `TECH-02` e o alcance produtivo de `DQ-01`, `STORE-01` e `STORE-04` | capacity plan, custo, backfill real, alternativas B/C, hierarquia empresarial dinamica e prova de escala/SLA |

Os status oficiais nao mudam neste gate: esta e evidencia de desenho, nao de
implementacao.

## Caso de negocio

Esta camada analitica existe para transformar registros ficticios de avaliacao
por categoria em indicadores agregados de volume e pontuacao, permitindo que a
Diretoria de Operacoes e analistas autorizados comparem categorias sem
consultar raw nem expor payloads.

Problema resolvido: o raw e adequado para auditoria operacional, mas nao oferece
um contrato estavel, minimizado e simples para consultas de decisao. O MVP deve
apoiar a comparacao de volume e pontuacao corrente entre categorias e, quando
houver fontes semanticamente compativeis, entre origens autorizadas.

## Consumidores

| Consumidor | Necessidade | Detalhe | Consulta |
| --- | --- | --- | --- |
| Diretoria de Operacoes | acompanhar volume e pontuacao por categoria | agregado institucional | KPIs, comparacoes e ranking |
| Analista de dados autorizado | validar metricas, distribuicao e lineage | agregado por categoria e fonte; identidade tecnica interna apenas para reconciliacao | agrupamentos, filtros e reconciliacao |
| Dashboard do MVP | servir somente indicadores aprovados | agregado, sem payload ou business key | consultas predefinidas sobre analytics |

## Perguntas analiticas do MVP

1. Quantos registros de avaliacao correntes existem no total?
2. Qual e a pontuacao media corrente por categoria?
3. Quais sao as pontuacoes minima e maxima correntes por categoria?
4. Para fontes explicitamente declaradas como semanticamente compativeis, como
   volume e pontuacao media se distribuem por fonte?

O MVP nao responde tendencia temporal porque a fixture nao possui data de
negocio. Timestamp de sincronizacao nao sera apresentado como data do evento.

## Escolha do modelo

| Criterio | Star Schema | Snowflake |
| --- | --- | --- |
| Simplicidade | fato ligada diretamente a duas dimensoes | exige normalizacao e mais joins |
| Manutencao | contrato pequeno e visivel | mais objetos e dependencias |
| Clareza no BI | filtros diretos | navegacao mais complexa |
| Volume conhecido | suficiente para fixture e MVP; volume produtivo desconhecido | beneficio nao demonstrado |
| Atividade 3 | demonstra fato e dimensoes com baixo custo cognitivo | permitido, mas nao exigido |

Decisao: **Star Schema** no PostgreSQL/Supabase do projeto institucional, em
camada logica analytics separada do raw. Um warehouse externo e Snowflake ficam
condicionados a volume, SLA ou hierarquias que demonstrem beneficio concreto.

## Multi-source

- Fontes semanticamente compativeis podem alimentar a mesma fato somente sob
  contrato de campos, tipos, unidade e significado explicitamente aprovado.
- Fontes incompatíveis permanecem separadas. `SOURCE_A` (curso/status) nao
  alimenta `FACT_CATEGORY_SCORE`; `SOURCE_B` (categoria/pontuacao) alimenta o
  MVP. Nao existe join por `registro_id` entre elas.
- Source e uma dimensao porque suporta lineage, reconciliacao e futuro recorte
  de acesso.
- `data_source_id` e a natural key interna da origem. O BI recebe a surrogate
  `source_key` e uma `source_ref` tecnica curta, nunca spreadsheet ID.
- Adicionar outra origem a fato exige compatibilidade semantica; igualdade de
  colunas, business key ou posicao nao basta.

## Current e history

Opcao escolhida: **estado corrente somente**.

`raw_import_rows` e RAW HISTORY: evidencia operacional de mudancas. Ele nao e
copiado para analytics. ANALYTICAL HISTORY so sera criado se uma pergunta de
negocio exigir tempo ou versao historica. O MVP deriva de
`raw_current_rows`, preserva o ultimo conjunto analitico valido em caso de erro
e ignora tombstones nas metricas correntes.

`dim_date` nao e necessaria no MVP. O contrato nao possui data de negocio, e
`imported_at`, `last_seen_at` e timestamps de run descrevem o pipeline, nao o
evento avaliado. Se uma fonte futura trouxer data de negocio validada, uma
decisao incremental podera adicionar `DIM_DATE` com apenas `date_key`, `date`,
`day`, `month` e `year`.

## Identidade analitica

- Natural key da fato: `(data_source_id, row_key_hash)` da linha current.
- Surrogate key da fato: `category_score_key`, tecnica e sem significado.
- Unicidade obrigatoria: uma linha da fato por `(source_key,
  source_record_key)`; `source_record_key` deriva de `row_key_hash` e permanece
  interno.
- Natural key de Source: `data_source_id`; surrogate: `source_key`.
- Natural key de Category no MVP: `(source_key, normalized_category)`;
  surrogate: `category_key`. Categorias so se tornam conformadas entre fontes
  mediante mapa semantico aprovado.
- `source_row_number` e posicao na planilha nunca participam da identidade.
- Hash nao e anonimo: chaves e hashes internos nao sao expostos no dashboard.

## Contrato da fato

### `FACT_CATEGORY_SCORE`

**Grain:** uma linha representa o estado analitico mais recente de um registro
de avaliacao identificado de forma unica por fonte e business key.

**Keys:**

- `category_score_key`: surrogate PK;
- `source_key`: FK para `DIM_SOURCE`;
- `category_key`: FK para `DIM_CATEGORY`;
- `source_record_key`: identidade tecnica interna, unica com `source_key`.

**Measures e estado:**

- `score_value`: pontuacao numerica armazenada;
- `is_current`: indica se o registro participa das metricas correntes.

**Degenerate dimensions:** nenhuma no MVP.

**Source lineage:** `data_sources` + `raw_current_rows` da fonte compativel,
identificados internamente por `data_source_id` e `row_key_hash`. O payload
completo nao e promovido.

## Contrato das dimensoes

### `DIM_SOURCE`

- PK: `source_key`.
- Natural key: `data_source_id`, somente interna.
- Attributes: `source_ref`, `source_name` ficticio/curado e
  `semantic_contract_version`.
- Source: `data_sources` e configuracao versionada.
- Relacao: uma Source para muitos fatos.
- Cardinalidade: baixa.
- Historical strategy: `SCD = not required for MVP`.

### `DIM_CATEGORY`

- PK: `category_key`.
- Natural key: `(source_key, normalized_category)`.
- Attributes: `category_label` minimizado e `category_code` normalizado.
- Source: campo `categoria` aprovado no contrato da fonte.
- Relacao: uma Category para muitos fatos.
- Cardinalidade: baixa a media.
- Historical strategy: `SCD = not required for MVP`.

## Metricas

| Nome tecnico | Nome de negocio | Definicao | Tipo | Grain | Agregacao | Origem | NULL | Dupla contagem | Materializacao |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `score_value` | Pontuacao | valor numerico validado do registro corrente | numeric | registro | soma apenas quando semanticamente aplicavel; base para avg/min/max | `pontuacao` | invalido/ausente bloqueia a linha; null permitido apenas quando `is_current=false` | unique por source/record e filtro current | armazenada |
| `current_record_count` | Registros correntes | quantidade de fatos com `is_current=true` | integer | consulta | count | estado da fato | zero sem linhas | unique por source/record | calculada no BI |
| `average_score` | Pontuacao media | media de `score_value` dos fatos correntes | numeric | categoria/fonte/total | avg | `score_value` | null quando nao ha fatos validos | filtro current e grain unico | calculada no BI |
| `minimum_score` | Menor pontuacao | menor `score_value` corrente | numeric | categoria/fonte/total | min | `score_value` | null sem fatos validos | filtro current | calculada no BI |
| `maximum_score` | Maior pontuacao | maior `score_value` corrente | numeric | categoria/fonte/total | max | `score_value` | null sem fatos validos | filtro current | calculada no BI |

## Contrato da transformacao

Fluxo conceitual:

```text
Google Sheets
      |
raw_current_rows          raw_import_rows
      |                   (evidencia; nao promovida)
      v
transformacao analitica idempotente
      |
DIM_SOURCE --- FACT_CATEGORY_SCORE --- DIM_CATEGORY
      |
      v
BI sobre objetos analytics aprovados
```

1. Entradas: `data_sources`, configuracao versionada e linhas nao deletadas de
   `raw_current_rows` para fontes vinculadas ao contrato.
2. Validacao: versao do contrato, campos obrigatorios, categoria nao vazia e
   pontuacao numerica; schema divergente bloqueia somente a fonte.
3. Normalizacao: trim controlado, categoria/codigo deterministico e conversao
   numerica sem inferencia silenciosa.
4. Deduplicacao: a unicidade operacional por fonte/key e revalidada pela
   natural key analitica; nenhuma regra usa numero da linha.
5. Lookups: Source por `data_source_id`; Category por source e valor
   normalizado.
6. Carga: criar ou atualizar dimensoes e fazer upsert da fato pela natural key;
   registros ausentes/deletados tornam-se `is_current=false`, sem DELETE.
7. Erro: falha de uma fonte nao publica conjunto parcial; conservar o ultimo
   conjunto analitico valido e emitir evidencia sanitizada.
8. Idempotencia: repetir o mesmo snapshot nao cria fato/dimensao nem altera
   medida; reconciliar contagens raw-current versus fato-current antes de
   publicar.

## Matriz de campos e minimizacao

| Campo candidato | Origem | Destino | BI? | PII potencial? | Transformacao | Observacao |
| --- | --- | --- | --- | --- | --- | --- |
| `data_source_id` | `data_sources.id` | natural key interna de `DIM_SOURCE` | no | no | lookup para surrogate | nunca expor como filtro externo |
| `source_ref` | referencia tecnica derivada | `DIM_SOURCE.source_ref` | yes | no, mas e linkavel | truncagem/allowlist | nao usar spreadsheet ID |
| `source_name` | configuracao curada | `DIM_SOURCE.source_name` | yes | possivel | allowlist para nome ficticio/negocial aprovado | nao copiar titulo da planilha automaticamente |
| `registro_id` | payload current | nenhum | no | yes/unknown | somente participa do hash operacional ja existente | permanece raw; nao expor |
| `row_key_hash` | current | `source_record_key` interno | no | yes/linkavel | manter interno | hash nao e anonimizacao |
| `categoria` | payload current | `DIM_CATEGORY` | yes | unknown | trim e codigo deterministico | aceitar somente taxonomia aprovada |
| `pontuacao` | payload current | `FACT_CATEGORY_SCORE.score_value` | yes | no isoladamente/unknown no contexto | parse numerico estrito | invalido bloqueia a linha/fonte conforme contrato |
| `curso` | payload de fonte incompatível | nenhum no MVP | no | unknown | nenhuma | permanece raw; outro caso exige outra decisao |
| `status` | payload de fonte incompatível | nenhum no MVP | no | unknown | nenhuma | nao promover por conveniencia |
| `payload_json` | raw | nenhum | no | yes | proibido na camada BI | nunca selecionar diretamente |
| `source_row_number` | raw | nenhum | no | no | descartado | instavel e proibido como identidade |
| timestamps de sync | raw/run | metadado tecnico fora da fato | no | no | preservar apenas para operacao | nao representar como data de negocio |
| `is_deleted` | current | `is_current` invertido/controlado | no | no | deleted vira current=false | dashboard filtra apenas current |

Campos `yes` chegam ao analytics somente no alcance ficticio. Para dados reais,
OD-07 e revisao DPO continuam obrigatorias.

## LGPD e acesso a dados

- Analytics recebe apenas Source curada, Category normalizada, score numerico e
  chaves tecnicas internas necessarias a integridade.
- Identificador original, linha fisica, payload, campos nao usados pelo BI e
  quaisquer dados pessoais permanecem fora de analytics.
- `payload_json`, `raw_current_rows` e `raw_import_rows` nao sao superficies de
  consulta do BI. Fluxo aprovado: **RAW -> ANALYTICS -> BI**.
- Hashes sao dados linkaveis, nao anonimos; ficam internos e protegidos.
- Campo novo nao e promovido automaticamente. Exige necessidade de BI,
  classificacao PII e atualizacao do contrato.
- O MVP usa fixtures. Dados reais exigem decisao de minimizacao/base legal,
  teste negativo de acesso e aceite dos responsaveis.

## Contrato futuro de RBAC/RLS

O projeto permanece isolado por instituicao. Dois papeis de leitura bastam ao
caso:

| Papel | Pode consultar | Recorte | Suporte de RLS |
| --- | --- | --- | --- |
| `analytics_manager` | metricas e dimensoes curadas de todo o projeto | project-wide | projeto institucional isolado |
| `analytics_source_reader` | os mesmos objetos, somente para fontes autorizadas | row-scoped | `FACT_CATEGORY_SCORE.source_key` e allowlist externa usuario/source |

O dashboard usa uma identidade de menor privilegio e nao recebe grants sobre
raw. Escrita em analytics pertence ao transformador, nao aos consumidores. A
hierarquia real, os usuarios e o provedor de identidade dependem de OD-06; os
nomes acima sao papeis tecnicos do MVP, nao cargos empresariais.

## BI MVP

| Visual | Pergunta | Metrica | Dimensao/filtro | Tipo |
| --- | --- | --- | --- | --- |
| Registros correntes | Q1 | `current_record_count` | Source opcional | KPI |
| Pontuacao media | Q2 | `average_score` | Source opcional | KPI |
| Pontuacao media por categoria | Q2/Q4 | `average_score` | Category; Source | barras |
| Faixa e volume por categoria | Q1/Q3 | count, min, max | Category; Source | tabela |

O dashboard e futuro; esta decisao apenas fixa o contrato que ele devera usar.

## Desenho logico

```text
DIM_SOURCE -------- FACT_CATEGORY_SCORE -------- DIM_CATEGORY
  source_key          category_score_key          category_key
  source_ref          source_key                  category_code
  source_name         category_key                 category_label
                      source_record_key
                      score_value
                      is_current
```

`DIM_DATE` nao integra o MVP.

## MVP PARA ENTREGA

1. Camada analytics no PostgreSQL/Supabase institucional, separada do raw.
2. `DIM_SOURCE`, `DIM_CATEGORY` e `FACT_CATEGORY_SCORE` conforme este contrato.
3. Transformacao idempotente da fixture `SOURCE_B`, sem copiar payload.
4. Reconciliacao de fatos correntes com raw current e teste de repeticao.
5. Consultas que comprovem count, average, min e max por Category/Source.
6. Dois escopos ficticios de leitura: projeto e fonte, com teste negativo.
7. Dashboard MVP com quatro elementos sobre analytics, nunca raw.
8. Medicao local declarada, sem extrapolar escala produtiva.

## FUTURO / PRODUCAO

- `DIM_DATE` quando houver data de negocio;
- historia analitica e SCD somente quando perguntas exigirem;
- taxonomia de Category conformada entre fontes;
- novas fatos para fontes semanticamente incompatíveis;
- warehouse externo, particionamento e tuning apos volume/SLA;
- hierarquia empresarial, identidade real e policies dinamicas;
- escolha/homologacao do BI, capacity plan, custos e planos B/C;
- dados reais, classificacao PII, base legal e aprovacoes;
- backfill/onboarding produtivo, scheduler e operacao continua;
- executor/scheduler/canal administrativo de retencao e otimizacao de locks.

## Criterios do proximo gate: `analytical_schema`

- uma migration incremental, somente local e revisada, representa exatamente a
  fato e as duas dimensoes, sem editar migrations anteriores;
- objetos analytics nascem fechados para papeis de frontend;
- PKs, FKs e unicidade refletem as natural/surrogate keys definidas;
- nao existe coluna para payload, spreadsheet ID, registro original ou linha;
- fixture ficticia pode ser carregada pela futura transformacao sem schema
  ambiguo;
- repeticao nao duplica dimensoes ou fato;
- estado nao current nao entra nas metricas;
- consultas previstas retornam resultados reconciliaveis;
- teste negativo impede leitura raw e acesso fora do source scope;
- testes estruturais e comportamentais ficam verdes;
- nenhuma alegacao de escala, LGPD produtiva ou BI implementado e feita sem
  evidencia.

## Traceability do contrato

| Requisito oficial | Decisao analitica | Futuro objeto | Evidencia necessaria |
| --- | --- | --- | --- |
| `OBJ-01`, `OBJ-02` | completar RAW -> ANALYTICS -> BI com fixture | transformacao + Star + dashboard | E2E ficticio reconciliado e repetivel |
| `OBJ-03`, `DQ-03` | minimizar campos e impedir BI sobre raw | grants/RLS analytics + views curadas | inventario PII e testes negativos |
| `DQ-01` | medir consultas sem prometer capacidade desconhecida | consultas/benchmark local | volume declarado e tempos observados |
| `DQ-02` | reutilizar PostgreSQL/Supabase no MVP | camada analytics no projeto | limites/custo datados no gate de viabilidade |
| `PROC-01` | contrato de schema por fonte antes da transformacao | validator/mapeamento versionado | drift bloqueia publicacao e preserva ultimo valido |
| `PROC-05` | uma fato e duas dimensoes, sem abstracao generica | Star Schema minimo | revisao de simplicidade e testes legiveis |
| `STORE-01` | PostgreSQL/Supabase como banco analitico do MVP | camada analytics | schema local, consultas e benchmark |
| `STORE-02` | raw e entrada, nao superficie de BI | lineage raw-current -> analytics | reconciliacao por fonte/key |
| `STORE-03` | Star Schema corrente de categoria/pontuacao | `FACT_CATEGORY_SCORE`, `DIM_SOURCE`, `DIM_CATEGORY` | migration, transformacao e metricas testadas |
| `STORE-04` | acesso project-wide e row-scoped por Source | policies/grants futuros | dois perfis ficticios e teste negativo |
| `WF-04`, `WF-05`, `WF-06` | representar transformacao, analytics e BI/RLS | Draw.io futuro | diagrama corresponde aos objetos validados |
| `AVAIL-01` | publicar atomicamente e conservar ultimo analytics valido | unidade de transformacao | falha simulada nao altera conjunto publicado |

