# Workflow

1. Uma resposta e registrada no Google Forms e aparece no Google Sheets.
2. Na Fase 1, um CSV ficticio representa a leitura da origem.
3. O sincronizador normaliza colunas e valores, calcula hashes e compara o snapshot anterior.
4. Ele registra linhas novas, alteradas, removidas, restauradas e duplicadas; tambem sinaliza mudancas de schema.
5. Sao gerados snapshot, manifest JSON, relatorio Markdown e SQL idempotente para revisao.
6. Em etapa posterior, o SQL revisado sera aplicado apenas no Supabase local; APIs reais entram na Fase 2.
