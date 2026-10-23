# Relatório Técnico da Sprint 07

## Identificação

**Projeto:** LoadForge — Stress and Resilience Evaluator
**Turma:** CC8NB — Fábrica de Software 2026.2
**Repositório:** [github.com/camimcl/sre-fabrica-de-software](https://github.com/camimcl/sre-fabrica-de-software)

| Integrante | Atuação no projeto |
|---|---|
| Camile Marcele Pereira de Araújo | Product Owner e Analista de QA |
| Ricardo Cezar Ottoni Assis de Almeida | Dados, infraestrutura e documentação |
| Aline Bianca Arantes da Silva | Desenvolvimento backend em Python |
| Emerson Wallace Barcelos de Araújo | Scrum Master e desenvolvimento backend |
| Cayo Vitor Fagundes | Desenvolvimento frontend e UI UX |

## Objetivo

A Sprint 07 consolida o sistema com recursos de consulta, análise e acompanhamento, integrados aos módulos já entregues (auth, projects, load_tests, metrics, intelligence, control, reports). A entrega cobre as seis frentes exigidas: dashboard, relatórios, pesquisa, filtros, exportação e logs/histórico de operações.

## Dashboard

Foi implementado um endpoint de indicadores agregados (`GET /projects/{id}/dashboard`) que calcula, a partir de dados reais do PostgreSQL: totais (execuções, cenários, endpoints, comparações), execuções por status e por estratégia, taxa de conclusão, desempenho médio (throughput, média dos P95 e taxa de erro das execuções concluídas) e uma série temporal de execuções por dia. O endpoint aceita um filtro de período. No frontend, o painel da Sprint 07 apresenta os indicadores em cartões e gráficos (distribuição e série temporal) desenhados em SVG, com filtro de período e tratamento de carregamento e erro.

## Relatórios

Os relatórios de execução e de comparação entre estratégias, entregues na Sprint 06, foram integrados ao novo painel e estendidos com consulta filtrável. O histórico de execuções passa a aceitar filtros e paginação, e os relatórios podem ser exportados (ver Exportação).

## Pesquisas

Foi adicionada busca textual, sem diferenciar maiúsculas de minúsculas e com escape de curingas, nas listagens de projetos (nome), cenários (nome) e usuários (nome e e-mail). Termos em branco são tratados como ausência de filtro.

## Filtros

As listagens de execução aceitam filtros por situação (status), categoria (estratégia), período (intervalo de datas) e usuário. Os filtros são conjuntivos e validados: valores fora do enum ou `date_from` posterior a `date_to` retornam 422 com mensagem clara. Todas as listagens relevantes passaram a oferecer paginação consistente (envelope com itens, total, página e tamanho de página) e ordenação determinística.

## Exportação

Foi implementada a exportação de dados e relatórios respeitando os filtros ativos:

- CSV do histórico de execuções e das comparações, com escapamento correto de vírgulas, aspas e quebras de linha (biblioteca padrão `csv`).
- PDF do relatório de execução e da comparação, com biblioteca `reportlab` (pura em Python).

A exportação XLSX não foi incluída: o CSV atende às necessidades de dados tabulares do projeto e é amplamente interoperável, portanto a ausência de XLSX é uma decisão consciente registrada aqui.

## Logs e histórico de operações

Foi criada uma trilha de auditoria (`operation_logs`) que registra as operações de escrita relevantes (criação, atualização, exclusão e transições de execução) com ator, ação, tipo de entidade, identificador, resumo de antes/depois e horário. O registro ocorre na mesma transação da operação auditada, de modo que um rollback descarta também o log correspondente; campos sensíveis (como hash de senha) nunca são registrados. A consulta (`GET /audit/logs`) é restrita ao perfil QA, com filtros por ator, ação, tipo de entidade e período, e paginação. O `actor_id` é preservado com `ON DELETE SET NULL`, mantendo o histórico mesmo após a remoção de um usuário. No frontend, uma aba de operações (visível apenas para QA) exibe o histórico paginado com filtros e o detalhe de antes/depois.

## Evidências da integração com os módulos anteriores

O dashboard e as consultas operam sobre os dados reais de projetos, cenários, execuções, janelas de métricas e comparações já existentes. As exportações usam os relatórios da Sprint 06. A auditoria é acionada pelas operações de escrita dos módulos de projetos, endpoints e execuções. A navegação do frontend integra a nova aba Dashboard às abas de Projetos, Execuções, Relatórios e Usuários.

## Verificação realizada

- Backend: suíte automatizada com pytest. A cobertura inclui filtros conjuntivos, busca case-insensitive, validação de intervalo de datas, paginação (limites e página além do total), dashboard sem dados, restrição do log de auditoria ao QA, registro de operações de escrita, equivalência de filtros entre consulta e exportação CSV, neutralização de injeção de fórmula em CSV, validação de escopo na exportação PDF de execução, ordem de rotas das exportações de comparação, normalização de datas com e sem fuso horário, e rejeição de projeto duplicado (409) sem deixar registro de auditoria. Os testes do motor de carga cobrem geração real contra alvo local, coleta de métricas, cancelamento e registro de transições.
- Integração com PostgreSQL 16 descartável (`loadforge_test`) sob o marcador `integration`, executável localmente com `LOADFORGE_TEST_DATABASE_URL` apontando para o banco migrado.
- Frontend: build de produção TypeScript + Vite aprovado (versão 0.7.0).
- Migração até `20261020_0007`, criando `operation_logs` sem alterar dados existentes.

## Ajustes de planejamento

- Nova dependência de runtime: `reportlab`, para geração de PDF (pura em Python, sem binários externos).
- Única estrutura de dados nova: `operation_logs` (auditoria), via migration encadeada; nada destrutivo.
- As capacidades de consulta foram adicionadas preferencialmente em rotas novas/agregadas e em parâmetros opcionais, preservando a compatibilidade com o consumo atual do frontend.

## Dificuldades encontradas

- Compatibilizar as agregações do dashboard entre SQLite (testes) e PostgreSQL (produção), resolvido com agregações portáveis e cálculo em Python quando necessário.
- Garantir a atomicidade da auditoria com a operação auditada, resolvido registrando o log na mesma transação, antes do commit do handler.
- Alinhar o ambiente local de dados científicos (numpy/scipy/scikit-learn) para rodar a suíte completa, resolvido fixando versões compatíveis no ambiente de desenvolvimento.

## Próximos passos

- Campanha experimental com modelo aprovado (recall ≥ 0,80) para comparação com evidência real de ganho da IA.
- Expandir a auditoria para operações de usuários e de modelos e enriquecer o dashboard com indicadores por estratégia ao longo do tempo.
- Possível exportação XLSX, caso surja necessidade específica.

## Conclusão

A Sprint 07 aproxima o LoadForge da conclusão funcional, entregando dashboard com dados reais, consultas com pesquisa e filtros, exportação em CSV e PDF e uma trilha de auditoria das operações, tudo integrado aos módulos anteriores e coberto por testes automatizados e build do frontend.
