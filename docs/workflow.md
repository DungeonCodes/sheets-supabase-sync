# Workflow

1. Uma fonte representa uma planilha e uma aba de uma instituicao.
2. Na Fase 1, um CSV ficticio representa a leitura da origem.
3. O sincronizador normaliza cabeçalhos para identificadores seguros, detecta colisões e propõe a tabela espelho da fonte.
4. Ele calcula hashes, compara snapshot, preserva payload bruto e identifica linhas e schema.
5. Mudanças bloqueantes (coluna ausente, renomeacao possivel ou tipo destrutivo) geram artefatos e exigem revisao humana, sem aplicar nem atualizar snapshot.
6. Fontes vencidas sao elegiveis a cada intervalo configurado (180 minutos no exemplo); uma falha nao interrompe as demais.
7. Google Sheets real e um scheduler de provedor entram em fases posteriores.
