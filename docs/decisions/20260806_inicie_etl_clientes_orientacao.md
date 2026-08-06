# ADR 20260806: Orientações da Inicie para o sistema ETL de clientes

## Status

Orientação recebida, pendente de análise e de decisões técnicas.

## Origem

Texto orientador enviado pela Inicie para a Atividade 3. Este registro preserva os requisitos, dúvidas e expectativas recebidos, mas não implica que ferramentas ou arquiteturas específicas já tenham sido aprovadas.

## Atividade 3 — Sistema ETL para clientes

### Objetivo

Desenvolver e estruturar uma nova arquitetura de dados (ETL/ELT) escalável, estável e de custo zero para substituir a atual dependência de fórmulas Google Sheets e Apps Script em planilhas Google de nossos clientes.

O sistema deve extrair dados, transformá-los de maneira robusta e disponibilizá-los em dashboards analíticos de alto desempenho, garantindo a proteção de dados sensíveis de nossos clientes.

### Diretrizes de desempenho e qualidade

- **Escala e desempenho:** suportar volumes crescentes de dados mantendo consultas e carregamento de dashboards ágeis.
- **Custo zero:** maximizar o uso de tecnologias open-source, planos gratuitos (free tiers) sustentáveis ou infraestruturas de custo zero.
- **Segurança e privacidade:** controle rigoroso de acesso e anonimização/tratamento de dados sensíveis dos clientes, em conformidade com a LGPD.
- **Manutenibilidade:** código limpo e de fácil manutenção, criando uma plataforma que utilize Python, ou outro sistema que atenda de forma eficiente às especificações, e permita a utilização de código SQL para tratamento dos dados.

## Estrutura do processo

É necessário avaliar e garantir que os sistemas escolhidos atendam aos requisitos críticos descritos abaixo.

### A. Ingestão e conectividade

- **Gestão de quotas e limites de API (rate limit):** mapear limites de requisição das fontes, como Google Forms, Google Sheets e APIs, para prevenir bloqueios ou falhas de sincronização.
- **Frequência de atualização:** definir a cadência do pipeline — batch periódico ou evento quase em tempo real — alinhada às necessidades operacionais dos clientes.

### B. Processamento, qualidade e resiliência (ETL/ELT)

- **Validação de esquema (schema drift):** o pipeline deve validar os tipos de dados e tratar exceções sem quebrar a execução total.
- **Monitoramento, logs e alertas:** criar mecanismo centralizado para registrar falhas, como estouro de limite de API, com rotinas automáticas e alertas por e-mail.
- **Simplicidade e padrão de código:** dar preferência a pipelines legíveis e reutilizáveis, evitando abordagens excessivamente complexas.

### C. Armazenamento, modelagem e segurança

- **Capacidade, escala e camadas de armazenamento:** definir um motor de banco de dados analítico ou Data Warehouse que suporte o crescimento do volume sem degradação de desempenho.
- **Modelagem analítica em SQL:** transformar dados brutos desnormalizados em modelos dimensionais, Star Schema ou Snowflake, com tabelas Fato e Dimensão para otimizar a velocidade de consulta dos dashboards.
- **Controle de acesso hierárquico (RLS/RBAC):** implementar controle fino de permissões de visualização, no qual usuários diferentes enxerguem apenas os dados para os quais possuem autorização dentro do mesmo dashboard ou tabela.

## Representação do workflow do processo

Deve-se pesquisar, testar e mapear a arquitetura ponta a ponta, criando também um fluxograma detalhado na plataforma Draw.io, sistema utilizado atualmente pela empresa para visualização e análise de processos. Esse material será necessário para validação técnica e apresentação à Diretoria de Operações.

### Etapas obrigatórias do fluxograma

1. **Fonte de dados — ingestão:** demonstrar como os dados saem do Google Forms/Sheets e identificar mecanismos de captura, como webhooks, conectores Python ou APIs.
2. **Camada de staging ou armazenamento bruto:** indicar o local de recepção inicial dos dados puros (raw data).
3. **Pipeline de transformação e qualidade (ETL/ELT):** incluir o ponto de validação de esquema (schema drift) e a transformação SQL para modelagem Star Schema.
4. **Camada de armazenamento analítico:** indicar o Data Warehouse ou banco de dados no qual ficarão os dados otimizados para consulta.
5. **Camada de serviço e visualização:** representar a conexão com a ferramenta de BI e a aplicação de filtros de segurança por nível de usuário (RLS).
6. **Camada transversal de observabilidade:** mapear onde os logs serão armazenados e por qual meio os alertas de falha serão enviados.

### Observação crucial

Cada etapa do fluxograma precisa conter caixas de texto ou anotações que destaquem:

- ferramentas testadas ou recomendadas para a etapa;
- pontos de atenção relativos à segurança e ao vazamento de dados;
- limitações operacionais ou de quota do sistema escolhido.

## Gestão de risco e viabilidade técnica — dúvidas

### A. Custos e limites de escalabilidade

- Se o requisito de custo zero não for possível no longo prazo, qual será o custo estimado de infraestrutura?
- Se o requisito de custo zero não for possível, quais são os limites exatos do plano gratuito de cada ferramenta escolhida?
- A infraestrutura escolhida possui cobrança sob demanda (pay-as-you-go) que possa crescer de forma descontrolada em picos de uso?

### B. Impacto no cliente e fricção operacional

- O cliente precisará instalar softwares, criar contas ou conceder permissões em quais sistemas?
- Como será feito o processo de onboarding e migração do histórico?
- Quando um cliente novo entrar ou um cliente antigo migrar, qual será o passo a passo para carregar seu histórico de dados na nova estrutura?

### C. Dependência tecnológica e continuidade

- Caso alguma ferramenta gratuita seja descontinuada ou altere repentinamente as políticas do plano gratuito, quais ferramentas poderão substituí-la de forma equivalente?
- Devem ser listadas as ferramentas aplicadas e suas respectivas opções de substituição, incluindo planos B e C.
- Qual é o nível de complexidade da manutenção diária?
- Caso o responsável pelo projeto deixe a empresa, outro profissional com conhecimentos básicos de Python conseguirá manter e corrigir o sistema?

### D. Disponibilidade, segurança e contingência

- Em caso de queda de servidor, falha de API ou erro na atualização do dashboard, o dashboard exibirá os últimos dados válidos ou uma tela de erro para o cliente?
- Onde e como serão armazenadas credenciais, chaves de API e senhas de acesso aos bancos de dados dos clientes?
- Deve-se garantir que senhas e chaves de API não fiquem expostas em código aberto ou scripts locais.

## Consequências para análise futura

As orientações acima deverão fundamentar pesquisas, provas técnicas, ADRs específicos e o fluxograma futuro. Decisões sobre ferramentas, custos, modelagem dimensional, BI, alertas, RLS/RBAC, onboarding e contingência ainda precisam ser avaliadas separadamente antes de serem consideradas aceitas.
