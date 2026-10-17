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

As entidades `comparison_reports` e `comparison_report_executions` mantêm a evidência e as nove ou mais execuções utilizadas. A impressão SHA-256 das condições facilita identificar comparações equivalentes. A migration `20261015_0005` cria essas tabelas e `20261016_0006` acrescenta o snapshot do alvo efetivamente carregado pelo motor (endpoint, URL, método HTTP e duração nominal das janelas). Alterações posteriores no cadastro não reescrevem esse registro. Históricos sem snapshot continuam consultáveis, mas exigem novas execuções para gerar uma comparação verificável; não há preenchimento retroativo inventado.

O campo comparativo `latency_p95_ms` representa estatísticas da **média dos P95 das janelas por execução**, não um percentil global das requisições. O throughput usa o tempo observado nas janelas, excluindo intervalos de persistência entre elas. O campo legado `final_error_rate` contém a taxa agregada de erro, enquanto `final_latency_p95_ms` corresponde à última janela. Esses significados são explicitados na interface e nas definições do resultado.

A comparação também conta janelas com inferência, fallback por regras e ausência de comprovação, além de identificar as versões dos modelos. Fallback, registros incompletos ou modelos diferentes geram ressalvas: os deltas não demonstram contribuição exclusiva da IA. Comparações históricas sem essa auditoria recebem aviso na interface.

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

As mensagens de validação HTTP `422` passaram a apresentar os campos e motivos informados pela API. A interface também mostra a meta de recall, se ela foi atingida e o limiar de decisão da versão aprovada. Relatórios exibem deltas, condições completas, identificadores das execuções e auditoria de fallback; deltas com base zero são apresentados como indisponíveis. A seleção limita comparações a 90 execuções e impede ações simultâneas enquanto uma operação está em andamento.

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

Na verificação final de 16/10/2026, sobre a `main` que incorporou o PR #4 de integração contínua, o backend concluiu **77 testes aprovados, zero falhas e zero ignorados**, com PostgreSQL 16 descartável e separado do banco em uso. A suíte inclui nove execuções HTTP reais locais em ordem rotativa, geração da comparação, consulta posterior e aviso de fallback. Um teste adicional de persistência gera os relatórios sobre o esquema migrado no PostgreSQL, fecha a conexão e recupera o mesmo resultado e os nove vínculos em uma nova sessão. As últimas asserções de autenticação, perfil visualizador e validação foram novamente verificadas na suíte de relatórios (10 testes aprovados).

O frontend concluiu TypeScript e build Vite de produção. A auditoria npm inicialmente encontrou uma vulnerabilidade alta em `source-map-js`; o lockfile foi atualizado para `1.2.2`, e a instalação limpa no build Docker novamente reportou zero vulnerabilidades. A revisão React orientou o controle de requisições, bloqueio de operações concorrentes e detalhes expansíveis acessíveis. Nesta verificação, não houve nova inspeção visual automatizada do navegador; build e testes HTTP não a substituem.

Os builds Docker da API e do frontend foram concluídos com sucesso usando os Dockerfiles do repositório. Os contêineres existentes de desenvolvimento não foram substituídos; o PostgreSQL de verificação foi criado separadamente.

O rebase preservou o workflow e o guia de integração contínua. O `uv.lock` está alinhado à versão `0.6.0` do `pyproject.toml`. Nesta verificação o Docker estava disponível: as migrations até `20261016_0006` e os testes PostgreSQL foram executados, incluindo preservação do histórico e rejeição de conflitos de limites antigos. A suíte local usa Python 3.12; o build da imagem da API usa Python 3.11. Avisos de depreciação de TestClient/httpx e da configuração Alembic permanecem, sem falhas. A branch incorpora a `main` `5fdf365`, confirmada novamente no remoto; nenhum pull request foi criado para disparar CI.

O resultado histórico da Sprint 05 permanece: F1 `0,82609` e recall `0,70370`. Ele demonstra a limitação que motivou a mudança, não o cumprimento retroativo da meta. O próximo treino só será aprovável se o recall final registrado for pelo menos `0,80`.

## Critérios da Sprint 06

| Critério | Situação | Evidência |
|---|---|---|
| Terceiro módulo implementado | Atendido | Serviço, API, tabelas, migration, testes e tela de relatórios. |
| Integração entre módulos | Atendido | Histórico usa projetos, cenários, execuções e métricas; comparação cobre as três estratégias. |
| Melhorias na interface | Atendido | Navegação por áreas, seletor de contexto, estados de meta, filtros e resultados comparativos. |
| Ajustes de navegação | Atendido | Troca de módulos e projetos, descarte de respostas atrasadas e permissões coerentes. |
| Evidência de ganho da IA | Pendente de campanha representativa | O teste integrado executou tráfego local real, mas sem modelo aprovado, com fallback. Não substitui a campanha com modelo real, alvo representativo e análise experimental. |

## Como demonstrar

1. Entre como QA e abra Projetos para confirmar o endpoint autorizado.
2. Em Testes, crie cenários equivalentes para as três estratégias e execute três repetições de cada.
3. Em Relatórios, selecione as nove execuções. Tentar uma amostra incompleta ou incompatível deve produzir orientação clara.
4. Gere a comparação e mostre médias, dispersão, deltas, condições e conclusão.
5. Recarregue a aplicação e recupere a mesma comparação para demonstrar persistência.

## Conclusão

A Sprint 06 adiciona um terceiro módulo funcional e integrado e transforma o plano experimental em regras executáveis. A entrega introduz mecanismos para buscar e exigir a meta de recall, sem afirmar que a nova meta já foi demonstrada em dados representativos. A equipe ainda precisa executar e registrar novo treino e campanha controlada com modelo aprovado para sustentar uma conclusão de ganho ou limitação da IA. O teste HTTP local de fallback valida integração, não essa hipótese experimental.
