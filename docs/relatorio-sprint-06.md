# Relatório Técnico da Sprint 06

## Objetivo

A Sprint 06 consolida a passagem de “o módulo funciona” para “o comportamento pode ser medido e comparado”. A entrega corrige primeiro os pontos da avaliação anterior e, sobre essa base, implementa o terceiro módulo do LoadForge: histórico e relatórios experimentais.

## Tratamento formal do feedback da Sprint 05

| Feedback | Alteração | Evidência verificável |
|---|---|---|
| IA e controlador foram antecipados | O cronograma oficial foi revisado e a avaliação experimental passou formalmente para a Sprint 06. | `docs/cronograma-sprints.md` |
| Recall `0,70370` abaixo da meta `0,80` | O resultado histórico foi preservado. Novos treinos calibram o limiar no conjunto de validação, usam balanceamento de classes e priorizam candidatos que atinjam recall `0,80`. A API bloqueia a aprovação abaixo da meta. | Testes de seleção de limiar, treino, aprovação e inferência; metadados `recall_target`, `recall_target_met` e `decision_threshold`. |
| Faltava comparar as três estratégias | O novo serviço exige `FIXED`, `RULES` e `AI_HYBRID`, pelo menos três repetições por estratégia, quantidades balanceadas e condições equivalentes. | Testes de rejeição, agregação, persistência e fluxo HTTP. |
| Ganhos e limitações precisavam de evidência | O relatório guarda médias, dispersão, extremos e deltas percentuais e inclui uma conclusão que proíbe inferir significância ou generalização. | `comparison_reports.results_json`, impressão digital das condições e texto de conclusão. |

A calibração do limiar usa apenas a partição de validação. O conjunto de teste continua reservado à estimativa final, evitando escolher o limiar com conhecimento do próprio teste. A aprovação não promete que toda base futura atingirá a meta; ela garante que a versão não seja promovida quando sua medição registrada estiver abaixo do critério definido pela equipe.

## Terceiro módulo implementado

O módulo `reports` entrega o fluxo:

`execuções persistidas → relatório individual → seleção balanceada → validação das condições → estatísticas por estratégia → comparação persistida → consulta na interface`

O relatório individual agrega requisições, sucessos, timeouts, duração observada, throughput, p95, taxa de erro, pico de concorrência e conformidade das janelas. A comparação agrupa esses relatórios e registra média, desvio-padrão populacional, mínimo e máximo de throughput, p95, erro e conformidade, além dos deltas de `AI_HYBRID` contra `FIXED` e `RULES`.

As entidades `comparison_reports` e `comparison_report_executions` mantêm a evidência e as nove ou mais execuções utilizadas. A impressão SHA-256 das condições facilita identificar comparações equivalentes. A migration `20261015_0005` e o esquema de referência foram atualizados em conjunto.

## Integração entre módulos

| Origem | Integração no terceiro módulo |
|---|---|
| Projetos e endpoints | A comparação pertence a um projeto e exige o mesmo endpoint. |
| Cenários e execuções | Os snapshots de duração, concorrência, ramp-up, timeout e limites formam as condições comparáveis. |
| Métricas | Os relatórios são calculados exclusivamente das janelas persistidas. |
| Inteligência | `AI_HYBRID` usa a versão aprovada e o limiar versionado; modelos sem a meta não podem ser aprovados. |
| Controle | As estratégias `RULES` e `AI_HYBRID` continuam produzindo decisões por janela. |
| Autorização | Visualizadores consultam; somente o QA proprietário gera os relatórios e comparações. |

## Interface e navegação

A aplicação passou a ter navegação principal explícita entre Projetos, Testes, Relatórios e Usuários. Nas áreas dependentes de contexto, o seletor de projeto permanece visível e evita que o usuário volte à tela de cadastro apenas para trocar o conjunto de dados.

Na tela de Relatórios, o usuário pode filtrar o histórico por estratégia, gerar um relatório individual, selecionar execuções concluídas e acompanhar a contagem de repetições. O botão comparativo só é habilitado quando há ao menos três seleções por estratégia e a quantidade está balanceada; o backend repete a validação e também confere as condições. Respostas atrasadas de um projeto anterior são descartadas para impedir mistura de informações após uma troca rápida de contexto.

As mensagens de validação HTTP `422` passaram a apresentar os campos e motivos informados pela API. A interface também mostra a meta de recall, se ela foi atingida e o limiar de decisão da versão aprovada.

## Protocolo experimental

Para uma comparação válida, a equipe deve:

1. utilizar um alvo local ou expressamente autorizado e registrar sua versão;
2. manter endpoint, duração, concorrência inicial e máxima, ramp-up, timeout, p95 limite e erro limite idênticos;
3. executar `FIXED`, `RULES` e `AI_HYBRID` em ordem alternada para reduzir viés temporal;
4. concluir no mínimo três repetições de cada estratégia;
5. evitar outras cargas concorrentes no gerador e no alvo;
6. gerar a comparação na tela Relatórios e preservar seu identificador;
7. analisar média e dispersão, não apenas o melhor valor isolado;
8. registrar falhas, aquecimento, versão do alvo e qualquer descarte de repetição.

O backend garante os itens que podem ser deduzidos dos dados persistidos. Versão do alvo, interferência externa e ordem alternada dependem do procedimento do laboratório e devem constar da ata da execução.

## Resultados e limitações

A suíte automatizada usa uma base determinística de três repetições por estratégia para provar a matemática, as rejeições e a persistência do relatório. Esses valores são dados de teste conhecidos e **não são apresentados como ganho real de `AI_HYBRID`**. Sem uma nova sessão de laboratório com um alvo autorizado e condições controladas, seria incorreto inventar uma conclusão de desempenho.

Na verificação de 15/10/2026, o backend concluiu **65 testes**, sem falhas, e ignorou cinco testes que exigem `LOADFORGE_TEST_DATABASE_URL`. O frontend concluiu a compilação TypeScript e o build Vite de produção. O teste HTTP do terceiro módulo autenticou um QA, criou uma comparação de nove execuções, recuperou o histórico com seus relatórios e consultou novamente a comparação persistida. A auditoria npm inicialmente encontrou uma vulnerabilidade alta na dependência transitiva `source-map-js`; o lockfile foi atualizado para `1.2.2` e a nova auditoria terminou com zero vulnerabilidades conhecidas.

O resultado histórico da Sprint 05 permanece: F1 `0,82609` e recall `0,70370`. Ele demonstra a limitação que motivou a mudança, não o cumprimento retroativo da meta. O próximo treino só será aprovável se o recall final registrado for pelo menos `0,80`.

## Critérios da Sprint 06

| Critério | Situação | Evidência |
|---|---|---|
| Terceiro módulo implementado | Atendido | Serviço, API, tabelas, migration, testes e tela de relatórios. |
| Integração entre módulos | Atendido | Histórico usa projetos, cenários, execuções e métricas; comparação cobre as três estratégias. |
| Melhorias na interface | Atendido | Navegação por áreas, seletor de contexto, estados de meta, filtros e resultados comparativos. |
| Ajustes de navegação | Atendido | Troca de módulos e projetos, descarte de respostas atrasadas e permissões coerentes. |
| Comparação experimental real | Preparada, aguardando sessão controlada | O produto executa e persiste a comparação; o repositório não inventa medições de um laboratório ainda não executado. |

## Como demonstrar

1. Entre como QA e abra Projetos para confirmar o endpoint autorizado.
2. Em Testes, crie cenários equivalentes para as três estratégias e execute três repetições de cada.
3. Em Relatórios, selecione as nove execuções. Tentar uma amostra incompleta ou incompatível deve produzir orientação clara.
4. Gere a comparação e mostre médias, dispersão, deltas, condições e conclusão.
5. Recarregue a aplicação e recupere a mesma comparação para demonstrar persistência.

## Conclusão

A Sprint 06 adiciona um terceiro módulo funcional e integrado e transforma o plano experimental em regras executáveis. A entrega melhora a meta de recall sem ocultar o resultado anterior e cria uma trilha persistente para comparações repetidas. A limitação restante é operacional e explícita: a equipe ainda precisa executar e registrar a sessão controlada no alvo autorizado para sustentar qualquer afirmação de ganho real.
