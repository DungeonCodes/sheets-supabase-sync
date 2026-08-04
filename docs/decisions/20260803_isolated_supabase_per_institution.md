# ADR 20260803: Supabase isolado por instituicao

## Status

Aceita.

## Contexto

O produto atende instituicoes com dados que nao devem coexistir no mesmo banco operacional. O modelo inicial continha estruturas de organizacao e projeto que sugeriam multitenancy desnecessaria.

## Decisao

- Cada instituicao possui um projeto Supabase independente.
- Nao ha multitenancy no banco desta versao; `organization_id` e `tenant_id` nao fazem parte do modelo.
- Uma `data_source` representa exatamente uma planilha e uma aba, e alimenta uma tabela espelho propria.
- Tabelas espelho nao possuem relacionamentos automaticos entre si.
- As tabelas operacionais ficam centralizadas dentro do projeto da instituicao e usam chaves estrangeiras apenas entre elas.
- O isolamento de dados e fornecido pelo projeto Supabase exclusivo da instituicao.

## Consequencias

Configuracoes e credenciais de backend selecionam o projeto da instituicao. A operacao de muitos projetos pode exigir revisao futura desta decisao caso o custo operacional se torne excessivo.
