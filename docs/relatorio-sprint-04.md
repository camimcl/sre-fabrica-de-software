# Relatório Técnico da Sprint 04

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

A Sprint 04 consolida a primeira parte funcional do sistema, avançando da estrutura da Sprint 03 para um módulo completo, integrado e utilizável. O módulo escolhido foi o de testes de carga (`load_tests`), o próximo passo natural após autenticação, projetos e endpoints já entregues. A partir dele, o sistema passa a permitir configurar cenários de teste, executá-los com ciclo de vida persistido e, sobre essa base, gerar carga HTTP real com coleta de métricas.

## Módulo implementado e funcionalidades

O módulo `load_tests` foi implementado em duas fases complementares.

### Fase A — Cenários e ciclo de vida das execuções

- **CRUD de cenários de teste** (`TestScenario`) aninhados sob um projeto e vinculados a um endpoint autorizado, com configuração de duração, concorrência inicial e máxima, ramp-up, timeout, estratégia e limites de segurança (p95 e taxa de erro).
- **Ciclo de vida das execuções** (`TestExecution`): criação em estado `PENDING`, transições `RUNNING`, `COMPLETED`, `CANCELLED` e `FAILED`, com uma máquina de estados que só permite transições válidas.
- **Snapshot de parâmetros**: ao criar uma execução, os parâmetros do cenário são copiados, preservando o histórico mesmo que o cenário seja editado depois.
- **Controle de acesso**: consultas para qualquer usuário autenticado; criação, edição, exclusão e operação de execuções apenas para o QA proprietário do projeto.

### Fase B — Motor de geração de carga real

- **Motor assíncrono** (`asyncio` + `httpx`) que, ao iniciar uma execução, dispara requisições HTTP concorrentes reais contra o endpoint autorizado, respeitando o plano de concorrência, o ramp-up e a duração configurados.
- **Coleta de métricas por janela temporal**: agrega throughput, latências p50/p95/p99, contagem de sucessos, erros e timeouts, persistindo um registro por janela em `metric_windows`.
- **Parada de emergência efetiva**: o cancelamento interrompe o disparo de novas requisições e finaliza a execução preservando os dados coletados.
- **Consulta por polling**: rota de leitura das janelas de métricas de uma execução, disponível durante e após o teste.

## Evidências do módulo funcionando

O funcionamento é demonstrável de duas formas: pela documentação interativa da API em `http://127.0.0.1:8000/docs` e pela suíte de testes automatizados.

Fluxo completo demonstrável:

1. Autenticar como QA e criar um projeto e um endpoint com autorização confirmada.
2. Criar um cenário de teste (`POST /projects/{id}/scenarios`).
3. Criar uma execução (`POST .../executions`) com `authorization_acknowledged`.
4. Iniciar a execução (`POST .../executions/{id}/start`) — o motor dispara carga real.
5. Acompanhar as janelas de métricas (`GET .../executions/{id}/metric-windows`).
6. Cancelar (parada de emergência) ou aguardar a conclusão por duração.

Resultado da suíte automatizada: **39 testes passando, 1 ignorado** (o teste de integração PostgreSQL, que exige um banco descartável configurado). Os testes do motor exercem a geração de carga contra um servidor-alvo HTTP local, sem dependência de rede externa.

## Evidências da persistência de dados

- Cenários e execuções são gravados no PostgreSQL por transações confirmadas (commit) e recuperados em consultas subsequentes; um teste específico reabre a sessão e confirma que o registro sobrevive.
- As janelas de métricas coletadas pelo motor são persistidas em `metric_windows` durante a execução e permanecem disponíveis após o término.
- O volume nomeado `loadforge_pgdata` do Docker Compose preserva os dados entre reinicializações da aplicação, atendendo ao requisito de disponibilidade após encerramento e reabertura.

## Exemplos das validações implementadas

Validações de formulário e de regra de negócio nos cenários:

- Campos obrigatórios e limites: `name` não vazio (até 120 caracteres); concorrências, duração, timeout e p95 com valor mínimo de 1; `ramp_up_per_window` maior ou igual a 0.
- Regra de concorrência: `initial_concurrency` deve ser menor ou igual a `max_concurrency`.
- Faixa de valores: `error_rate_limit` entre 0 e 1.
- Estratégia restrita aos valores válidos (`FIXED`, `RULES`, `AI_HYBRID`).
- Rejeição de campos não previstos no formulário.

Validações de execução:

- Só é possível criar uma execução com a autorização reconhecida (`authorization_acknowledged`).
- Só é possível iniciar uma execução cuja autorização foi reconhecida.
- O cancelamento exige um motivo.
- Invariante de segurança: um cenário só pode referenciar um endpoint com autorização confirmada, e o motor só gera carga contra alvos autorizados.

## Evidências das mensagens de erro

O sistema retorna mensagens claras e o código HTTP adequado a cada situação, sem falhas técnicas sem tratamento:

| Situação | Código | Mensagem |
|---|---|---|
| Sem credenciais válidas | 401 | Invalid or expired credentials |
| Usuário sem papel QA | 403 | QA role required |
| QA não proprietário do projeto | 403 | Project owner required |
| Projeto/endpoint/cenário/execução inexistente | 404 | Mensagem específica ("... not found") |
| Endpoint sem autorização confirmada | 409 | The target endpoint must have confirmed authorization before scenarios can target it |
| Transição de estado inválida | 409 | Invalid execution state transition |
| Iniciar sem reconhecer autorização | 409 | authorization_acknowledged must be true to start an execution |
| Excluir cenário com execuções dependentes | 409 | Remove dependent executions before deleting the scenario |
| Dados de formulário inválidos | 422 | Mensagem específica do campo |

## Demonstração do fluxo de navegação entre as telas

A navegação entre telas é responsabilidade da frente de frontend (React), que consome a API deste módulo. O fluxo de referência (protótipo em `docs/prototypes/flow.md`) percorre: Login → Dashboard → Novo cenário → Iniciar execução → Monitoramento → Parada de emergência → Conclusão → Histórico. O backend desta sprint fornece todos os endpoints necessários para esse fluxo, documentados em `/docs`. As dependências entre backend e frontend estão registradas em `docs/sprint-04-dependencias-fora-backend.md`.

## Ajustes de planejamento e arquitetura

Conforme permitido pelo critério da sprint, registram-se os seguintes ajustes:

- **Faseamento da entrega:** o módulo foi dividido em Fase A (cenários e ciclo de vida) e Fase B (motor de carga real). A Fase A garante um módulo completo e persistido; a Fase B agrega o diferencial de geração de carga real. Ambas foram concluídas e commitadas de forma incremental.
- **Persistência do motor assíncrono:** o motor dispara HTTP de forma assíncrona, mas grava as métricas usando a sessão síncrona existente executada fora do event loop (`asyncio.to_thread`), mantendo a infraestrutura de banco e os contratos da Fase A intactos, sem introduzir um driver assíncrono novo.
- **Limitação conhecida:** as colunas `cpu_percent` e `memory_mb` das janelas são preenchidas com a utilização local do processo (ou zero, quando indisponível no sistema operacional), pois a medição de CPU/memória do alvo está fora do escopo desta versão enxuta.

## Repositório e organização dos commits

O desenvolvimento foi realizado na branch `sprint-4`, com commits incrementais e descritivos que acompanham a evolução (schemas, API, máquina de estados, motor, testes e documentação), evitando um único envio próximo ao prazo. O link do repositório é [github.com/camimcl/sre-fabrica-de-software](https://github.com/camimcl/sre-fabrica-de-software).

## Dificuldades encontradas

- Coordenar a execução assíncrona do motor de carga com a persistência síncrona do projeto, sem bloquear a API nem alterar a base já entregue.
- Garantir que a introdução do motor não quebrasse o comportamento de transições manuais da Fase A, resolvido com um controle de ativação do motor e testes de regressão.
- Reproduzir cenários de erro e timeout de forma determinística nos testes, resolvido com um servidor-alvo HTTP local descartável.

## Próximos passos

- Integrar a previsão local de risco (`intelligence`) e o controlador adaptativo (`control`) ao laço entre janelas, permitindo ajuste dinâmico da concorrência.
- Consolidar os relatórios e a comparação entre as estratégias fixa, por regras e assistida por IA (`reports`).
- Integração do frontend com os novos endpoints para a demonstração de navegação ponta a ponta.
- Testes de integração em PostgreSQL para o novo módulo, sob o marcador `integration`.

## Conclusão

A Sprint 04 entrega o primeiro módulo completo do LoadForge, com fluxo real e integrado, persistência demonstrável, validações, mensagens de erro tratadas e a base de API para a navegação entre telas. Além do escopo mínimo, o motor de geração de carga real foi implementado e testado, aproximando o sistema do seu diferencial de avaliação de resiliência sob carga.
