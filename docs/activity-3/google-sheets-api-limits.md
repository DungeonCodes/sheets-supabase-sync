# Limites da Google Sheets API na Fase 1

Consulta realizada em **2026-08-06**, exclusivamente em documentação oficial do Google. Valores podem mudar; a cota efetiva do projeto deve ser conferida no Google Cloud antes de produção.

## Limites técnicos publicados

| Item | Limite ou comportamento oficial | Impacto |
| --- | --- | --- |
| Leituras por minuto por projeto | 300 | Cada fonte usa atualmente duas leituras: metadados e valores. |
| Leituras por minuto por usuário por projeto | 60 | Chamadas da Service Account contam como um único usuário, portanto este é o teto conservador dominante para uma credencial compartilhada. |
| Reposição | A cada minuto | Uma rajada não pode consumir antecipadamente a janela seguinte. |
| Excesso temporal | HTTP 429 | Deve usar backoff exponencial truncado; repetição imediata aumenta o problema. |
| Requisições diárias | Sem limite diário adicional enquanto as cotas por minuto forem respeitadas | Não elimina limites de processamento, tamanho ou eventual mudança comercial. |
| Payload | Não há máximo rígido próprio publicado; o Google recomenda até 2 MB | Ler apenas o intervalo necessário e limitar campos de metadados. |
| Processamento por requisição | Timeout do serviço após 180 segundos | O projeto usa timeout cliente muito menor para não bloquear um worker. |
| Concorrência por planilha | Recomendação de no máximo uma requisição por segundo | O scheduler futuro deverá serializar leituras da mesma planilha. |

Fontes: [Usage limits](https://developers.google.com/workspace/sheets/api/limits), [Troubleshoot API errors](https://developers.google.com/workspace/sheets/api/troubleshoot-api-errors) e [Batch requests](https://developers.google.com/workspace/sheets/api/guides/batch).

## Limites operacionais escolhidos pelo projeto

- Escopo OAuth único: `https://www.googleapis.com/auth/spreadsheets.readonly`.
- Duas requisições GET por execução nesta fase: metadados mínimos e valores de uma aba.
- Timeout cliente padrão: 15 segundos por requisição.
- Até quatro tentativas, backoff inicial de 1 segundo, teto de 16 segundos, jitter de até 20% e orçamento total de espera de 45 segundos.
- `Retry-After` prevalece quando for maior que o atraso calculado.
- Retry somente para 429, 500, 502, 503, 504, timeout e conexão temporária. Não há retry automático para 400, 401, 403 permanente, 404, configuração ou schema inválido.
- Nenhum rate limiter global ou scheduler foi implementado nesta fase. Até existir coordenação entre fontes, o orçamento operacional não deve exceder 30 leituras por minuto por Service Account (50% da cota por usuário publicada).

O teto de 30 leituras/minuto é uma escolha conservadora do projeto, não uma cota oficial. Com duas chamadas por fonte, equivale a até 15 execuções iniciadas por minuto sem retries. Essa conta não é dimensionamento aprovado: frequência, volume e número de clientes permanecem decisões abertas.

## Batch, frequência e crescimento

O leitor já restringe campos nos metadados e obtém os valores da aba em uma chamada. `batchGet` só passa a ser vantajoso quando uma execução precisar de vários intervalos; adicioná-lo agora aumentaria complexidade sem reduzir as duas chamadas de naturezas diferentes. O scheduler futuro deve distribuir fontes na janela, serializar a mesma planilha e observar 429/retries antes de elevar frequência.

Não é possível confirmar quase tempo real nem capacidade por cliente sem OD-01 (frequência), OD-02 (volume) e OD-03 (atraso aceitável). A estimativa deve considerar duas leituras por execução, retries, picos simultâneos e uma margem operacional.

## Custo e alerta temporal

Na data consultada, o Google informa que o uso padrão da Sheets API está disponível sem custo adicional, mas também anuncia que exceder limites de quota está planejado para gerar cobrança na conta de faturamento ainda em 2026. Portanto, custo zero permanece plausível apenas dentro das cotas e para o volume ainda desconhecido; não é garantia futura. Essa mudança potencial mantém R-01 e R-16 abertos e exige revisão antes de produção.

Aumento de quota depende de solicitação e aprovação; não é automático nem garantido. Fonte: [View and manage quotas](https://cloud.google.com/docs/quotas/view-manage).

## Evidência ainda necessária

- Conferir as cotas efetivas do projeto autorizado sem registrar identificadores.
- Medir payload, duração e chamadas na fixture real.
- Simular concorrência de múltiplas fontes e confirmar o orçamento.
- Definir frequência, volume e política de escalonamento com a empresa.
