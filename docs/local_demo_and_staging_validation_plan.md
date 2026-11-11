# Demonstração local e validação hospedada em staging

Este plano não autoriza acesso remoto, SQL, deployment, execução de workflow,
ativação de recorrência ou uso de dados reais. A evidência atual é PostgreSQL
local dedicado e dashboard local, não equivalência funcional com Supabase hospedado.

## Demonstração local

1. Confirmar contêiner dedicado saudável e dashboard em loopback. O operador
   acessa `http://127.0.0.1:3219`, usuário `dashboard`, com token obtido no arquivo
   local ignorado `runtime/local-dashboard-access-token.txt`; não mostrar o token.
2. Apresentar os agregados fictícios de Categoria X e Y, filtro e estado de leitura.
   Explicar que os valores finais 12 e 20 foram verificados por Playwright.
3. Mostrar a evidência registrada no run log: primeira carga, idempotência, update,
   tombstone, restore, reconciliação, RLS e testes de rollback. O teste de rollback
   em PostgreSQL verifica ausência de uma source recém-criada após quatro falhas;
   não é uma comparação direta de uma source preexistente antes e depois.
4. A fonte `fixture_dashboard` e seus dados persistem localmente. Não repetir
   operações ou limpar banco para apresentação; não usar a demo histórica como alvo.

## Plano único para staging

1. **Definir escopo e revisão.** Identificar projeto exclusivo da instituição,
   responsável, janela, SHA e arquivos exatos, banco e source fictícia isolada;
   verificar o estado efetivo de migrations e compatibilidade com Supabase. Revisar
   SQL e efeitos, especialmente a migration analítica candidata, dependências, seed,
   papéis, políticas, transações, limites e plano de recuperação. Não presumir que os
   papéis ou policies locais sejam adequados ao Supabase hospedado.
2. **Isolamento e segurança.** Revisar privilégios efetivos, RLS com identidades sem
   bypass, acesso cruzado negado, isolamento da source, segredos no servidor, logs
   sanitizados, TLS e autorização web apropriada. A autenticação Basic em loopback
   e as policies locais não autorizam exposição hospedada; criar desenho hospedado
   e validar que navegador não recebe credenciais privilegiadas ou payload raw.
3. **Preparar execução manual.** Fixar o código revisado, fixtures sintéticas,
   contagens esperadas, observabilidade e procedimento para falha e resultado de
   commit ambíguo. Confirmar opt-in de recorrência desligado. A aprovação específica
   do operador deve identificar destino, SQL, código, janela, acessos e alterações
   exatas; este plano não é essa aprovação. Não acionar GitHub Actions por padrão.
4. **Executar somente após autorização.** No escopo aprovado, validar primeira
   carga, repetição, update, tombstone, restore, drift, falha e recuperação, uma
   source não interferindo na outra e limites de leitura/escrita do papel real.
   Registrar IDs técnicos e contagens sanitizadas; falha, divergência ou incerteza
   interrompe o ciclo e requer reconciliação antes de qualquer nova tentativa.
5. **Reconciliar.** Comparar raw corrente, histórico por evento, execuções e fatos
   analíticos com os valores sintéticos esperados, incluindo o snapshot anterior
   após falha. Separar evidência de testes como owner da evidência com o papel
   restrito; não expor identificadores completos, payload, URL ou credenciais.
6. **Testar interface e desempenho.** Depois de aprovar o desenho hospedado,
   validar login, negação, categorias e filtros por navegador e controle de acesso
   por source. Com volume sintético e janela previamente definidos, medir latência,
   duração, concorrência, consumo e limites da API/banco; comparar com metas acordadas
   e parar diante de impacto não previsto. Nenhum benchmark remoto é autorizado aqui.
7. **Encerrar e decidir.** Registrar versão, escopo, evidências, resultados, desvios,
   responsável e decisão; não declarar produção pronta pelo sucesso do staging. Em
   falha preservar evidência e estado, suspender novas execuções e aplicar somente
   recuperação revisada e autorizada, sem exclusão ou reset automático.

O plano operacional de automação existente em `release_staging_preparation.md`
continua aplicável: o modo manual não comprova sozinho a origem humana, e a
recorrência não está autorizada. Não se deve inferir autorização de dispatch,
publicação ou mudança de variáveis a partir desta preparação.
