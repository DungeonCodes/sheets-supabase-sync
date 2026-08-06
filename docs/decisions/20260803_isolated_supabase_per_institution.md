# ADR 20260803: Supabase isolado por instituicao

## Status

Aceita.

Data: 2026-08-03.

## Contexto

O produto atende instituicoes com dados que nao devem coexistir no mesmo banco operacional. O modelo inicial continha estruturas de organizacao e projeto que sugeriam multitenancy desnecessaria.

## Decisao

- Cada instituicao possui um projeto Supabase independente.
- Nao ha multitenancy no banco desta versao; `organization_id` e `tenant_id` nao fazem parte do modelo.
- Uma `data_source` representa exatamente uma planilha e uma aba, e alimenta uma tabela espelho propria.
- Tabelas espelho nao possuem relacionamentos automaticos entre si.
- As tabelas operacionais ficam centralizadas dentro do projeto da instituicao e usam chaves estrangeiras apenas entre elas.
- O isolamento de dados e fornecido pelo projeto Supabase exclusivo da instituicao.

## Alternativas consideradas

- Banco unico multitenant, rejeitado pela complexidade e pelo risco de isolamento incorreto.
- Relacionamentos automaticos entre tabelas espelho, adiados porque as fontes nao possuem semantica relacional comprovada.

## Consequencias positivas

- Isolamento institucional fornecido pelo proprio projeto Supabase.
- Modelo operacional menor, sem identificadores de tenant em todas as tabelas.
- Falhas e evolucao de schema permanecem independentes por fonte.

## Consequencias negativas

Configuracoes e credenciais de backend selecionam o projeto da instituicao. A operacao de muitos projetos pode exigir revisao futura desta decisao caso o custo operacional se torne excessivo.

## Evolucao registrada em 2026-08-04

Antes do primeiro deploy, as tres migrations da PoC foram arquivadas e substituidas por uma baseline unica, sem multitenancy ou operacoes destrutivas. As migrations antigas nunca foram aplicadas; a nova baseline foi apenas lintada e validada em dry-run e aguarda revisao humana. Quando aplicada, nao devera ser reescrita: evolucoes posteriores usarao migrations incrementais.

Decisoes substituidas: nenhuma ADR aceita. A consolidacao substitui apenas migrations locais nao aplicadas da PoC.

## Evolucao registrada em 2026-08-06

A observacao de 2026-08-04 acima permanece como registro historico anterior ao deploy. A baseline corrigida foi posteriormente aplicada em 2026-08-05. Em 2026-08-06, inspecao independente e somente de leitura confirmou historico local/remoto convergente, cinco tabelas operacionais vazias, constraints e indices esperados, RLS/grants coerentes e Data API acessivel. A baseline continua imutavel; futuras mudancas exigem migrations incrementais.
