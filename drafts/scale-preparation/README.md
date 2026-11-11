# Preparação sintética de escala

Gerador determinístico, streaming, sem rede, arquivos temporários ou dados pessoais.
`python drafts/scale-preparation/generate.py --rows 10 --sheets 3 --seed 42`.
É um gerador de snapshots fictícios, não simula nem executa a sincronização real.
O consumidor controla seus arquivos; usar diretório temporário dedicado, espaço e
permissões adequados, sem sobrescrever dados e sem colocar artefatos no Git.

## Cenários a executar futuramente, em ambiente isolado aprovado

Usar mesma seed, contagem e número de planilhas em cada comparação:

| Cenário | Preparação sintética e verificação futura |
| --- | --- |
| Primeira carga | `initial`: carregar snapshot em estado vazio, conferir totais. |
| Sem mudanças | `unchanged`: repetir initial, conferir deltas zero e idempotência. |
| Incremental | `incremental`: modifica valor de cada décima linha, comparar deltas. |
| Inserções | `insert`: usar contagem maior; prefixo coincide com initial. |
| Exclusões lógicas | `delete`: status sintético deleted a cada décima linha. |
| Restaurações | `restore` após `delete`: status volta a active, sem perda de ID. |
| Falha entre lotes | Dividir em lotes controlados no consumidor; injetar falha após confirmação de um lote e conferir transação e evidências. |
| Reinício | Recomeçar no limite confirmado com `--start N`, sem duplicar cabeçalho na concatenação; reconciliar estado e totais. |
| Múltiplas sources | `--sheets 3` distribui IDs entre planilhas sintéticas; o consumidor deve mapear cada uma a uma source fictícia. |
| Estrutural | `structural` acrescenta uma coluna fictícia; validar política de schema antes de persistir. |

Propostas de volume: `--rows 300000` e `--rows 1000000`; não são requisitos
aprovados e não foram executadas. Fixar seed, commit, limites de recursos, tamanho
de lote e condições de parada. Separar medições de CPU, pico de memória e duração;
medir quotas, bursts e latência Google Sheets; conexões, locks, WAL e transações
PostgreSQL; custos e concorrência por source e cliente. Medir serviços reais somente
em ambiente e janela autorizados. Não extrapolar custos ou capacidade sem evidência.
