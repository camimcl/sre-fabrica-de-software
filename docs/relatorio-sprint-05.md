# Relatório Técnico da Sprint 05

## Identificação

**Projeto:** LoadForge — Stress and Resilience Evaluator  
**Turma:** CC8NB — Fábrica de Software 2026.2  
**Repositório:** [github.com/camimcl/sre-fabrica-de-software](https://github.com/camimcl/sre-fabrica-de-software)  
**Protótipo de referência:** [Figma — LoadForge Sprint 02](https://www.figma.com/design/isw6HZdCiomQvSekNScl9J)

| Integrante | Atuação no projeto |
|---|---|
| Camile Marcele Pereira de Araújo | Product Owner e Analista de QA |
| Ricardo Cezar Ottoni Assis de Almeida | Dados, infraestrutura e documentação |
| Aline Bianca Arantes da Silva | Desenvolvimento backend em Python |
| Emerson Wallace Barcelos de Araújo | Scrum Master e desenvolvimento backend |
| Cayo Vitor Fagundes | Desenvolvimento frontend e UI UX |

## Objetivo e continuidade

A Sprint 05 entrega o segundo módulo funcional do LoadForge: inteligência local e controle adaptativo. A Sprint 04 já permitia criar cenários, gerar carga HTTP e persistir janelas de métricas, mas as estratégias `RULES` e `AI_HYBRID` ainda não alteravam o comportamento do motor. Nesta entrega, as métricas passam a alimentar um pipeline de aprendizado de máquina e um controlador que ajusta a concorrência de forma auditável.

O protótipo no Figma continua sendo a referência visual compartilhada. A interface implementada nesta sprint é funcional e poderá evoluir após novos testes de usabilidade, sem alterar o fluxo técnico descrito neste relatório.

## Segundo módulo completo

O módulo combina duas responsabilidades inseparáveis no fluxo operacional:

1. `intelligence` transforma métricas históricas em amostras, treina modelos locais, registra métricas e disponibiliza uma versão aprovada para inferência;
2. `control` combina risco, latência p95 e taxa de erro para aumentar, manter ou reduzir a concorrência da janela seguinte.

Fluxo completo implementado:

`cenário autorizado → execução → janela de métricas → características → previsão local → decisão → nova concorrência → persistência`

O treinamento não consome API externa de IA. As características incluem concorrência, throughput, latências p50/p95/p99, erros, timeouts, CPU, memória e tendências entre janelas. O rótulo indica se haverá violação de p95 ou taxa de erro em alguma das cinco janelas seguintes, nominalmente equivalentes a dez segundos. São utilizadas execuções concluídas com sequências completas de janelas. A separação cronológica reserva 60% para treino, 20% para validação e 20% para teste, antes de excluir amostras cujos rótulos alcançam a partição seguinte. As três partições precisam conter as duas classes.

São comparados `LogisticRegression` e `RandomForestClassifier` com estado aleatório fixo. O candidato é escolhido por F1, seguido de recall e precisão, no conjunto de validação. Somente o vencedor é avaliado no teste independente. A versão registra algoritmo, precisão, recall, F1, acurácia, falsos positivos, quantidade de amostras, hash do conjunto, hash do artefato e metadados da divisão temporal.

## Integração com o banco de dados

| Operação | Persistência | Recuperação/atualização |
|---|---|---|
| Treinamento | Insere uma versão `CANDIDATE` em `model_versions`. | `GET /intelligence/models` recupera métricas e estado. |
| Aprovação | Atualiza o candidato para `APPROVED` e aposenta a versão aprovada anterior. | O motor consulta a única versão aprovada antes da execução híbrida. |
| Inferência | Insere uma `risk_prediction` vinculada à janela e ao modelo. | A interface consulta as previsões da execução. |
| Controle | Insere uma `control_decision` com estratégia, ação, concorrências e justificativa. | A interface consulta e exibe a decisão de cada janela. |
| Snapshot | A execução agora guarda também `ramp_up_per_window`. | Editar o cenário depois não altera o plano histórico. |

A migration `20261001_0003` adiciona o snapshot e os metadados auditáveis. A migration `20261001_0004` e o esquema SQL acrescentam um índice único parcial para impedir dois modelos aprovados simultaneamente. Ao migrar duplicatas históricas, a versão aprovada mais recente é preservada e as demais são aposentadas. A API desfaz a transação e retorna conflito quando aprovações concorrentes disputam essa restrição. As quatro migrations foram aplicadas no PostgreSQL 16. Os testes adicionais confirmaram preservação dos históricos compatíveis e rejeição preventiva dos incompatíveis, sem alterar os dados. Os artefatos locais são mantidos em volume Docker; o banco guarda o caminho relativo e o SHA-256 esperado.

Na execução híbrida `a45e7cef-db67-4ba4-a903-507ca824b2b5`, foram recuperadas quatro janelas, quatro previsões e quatro decisões associadas ao modelo `27d485d8-d171-4596-837a-8d40d825ad05`. Após reiniciar a API, os mesmos identificadores, estados e valores continuaram disponíveis. As respostas utilizadas na comparação estão no [registro do experimento](evidences/sprint-05/fluxo-api.json).

## Regras de negócio atualizadas

| Regra | Decisão e justificativa |
|---|---|
| Horizonte preditivo | Cinco janelas futuras, nominalmente dez segundos, com duração observada variável; não há garantia de antecipação em dez segundos exatos. |
| Base mínima | O treino exige ao menos 20 amostras e as duas classes nas partições cronológicas; sem isso, retorna conflito e não produz um modelo enganoso. |
| Aprovação única | Aprovar um candidato aposenta a versão anterior, permitindo saber exatamente qual modelo orientou uma execução. |
| Integridade do artefato | Caminho restrito ao diretório de modelos e validação de versão, esquema de atributos e SHA-256 antes de carregar `joblib`. |
| Estratégia por regras | Usa métricas atuais para aumentar, manter ou reduzir a concorrência e persiste a decisão. |
| Estratégia híbrida | Usa a probabilidade local como sinal adicional e persiste previsão e decisão. |
| Fallback | Sem modelo aprovado ou diante de erro de inferência, continua por regras e grava a causa na justificativa. |
| Limites operacionais | Duração até 3.600 s, concorrência até 500, timeout até 60.000 ms e p95 configurável até 300.000 ms. |
| Alvo autorizado | A criação e o início continuam condicionados à confirmação de autorização do endpoint. |

## Interface e navegação

O novo painel React mantém os cadastros existentes e adiciona:

- criação e seleção de cenários;
- criação e início de execução com reconhecimento de autorização;
- parada emergencial;
- atualização automática do estado durante a execução;
- tabela conjunta de métricas, risco e decisão por janela;
- listagem, treinamento e aprovação de versões do modelo.

Quando não existe modelo aprovado, a interface informa que o fallback por regras está ativo. O painel também mostra F1, recall, acurácia, algoritmo, quantidade de amostras e estado de cada versão.

## Testes e resultados

| Verificação | Resultado | Cobertura principal |
|---|---|---|
| Backend completo | **64 aprovados, zero falhas e zero ignorados** | Autenticação, persistência, motor, limites, IA, controle, APIs e segurança; dependências do lockfile. |
| Pipeline de IA | Aprovado | Horizonte temporal, treinamento, seleção, aprovação, inferência e rejeição de artefato adulterado. |
| Controle integrado | Aprovado | Decisão por regras, previsão híbrida, persistência e fallback sem modelo. |
| Motor de carga | Aprovado | Concorrência efetiva, erros, timeout, cancelamento e duração observada. |
| TypeScript | Aprovado | Compilação estática das telas existentes e do painel da Sprint 05. |
| Dependências Python | Aprovado no Windows com Python 3.11 | Ambiente novo instalado a partir do lockfile; 44 pacotes compatíveis; suíte concluída em 38,37 s. |
| Build de produção e navegador | Aprovado | Imagens construídas; login, criação, início, monitor, parada e recuperação exercitados com API real. |
| Docker Compose | Ambiente executado | API, frontend, PostgreSQL 16 e alvo HTTP controlado em laboratório isolado. |
| PostgreSQL real | Aprovado | Dois testes de integração e três casos de migração sobre históricos em schemas descartáveis. |
| Seleção durante resposta atrasada | Aprovado | Erro reproduzido antes da correção; seleção e monitor corretos após invalidar consultas antigas. |
| Monitor com consultas lentas | Aprovado | Respostas acima de dois segundos deixam de bloquear a atualização do estado terminal; polling sem sobreposição. |

A coleta FIXED de 480 segundos gerou 235 amostras utilizáveis. O candidato Random Forest registrou F1 0,82609, recall 0,70370 e acurácia 0,82979 no conjunto de teste cronológico. São resultados do alvo controlado, não comprovação de generalização nem de superioridade sobre outras estratégias. O fluxo integrado também verificou fallback, rejeição de treino insuficiente (HTTP 409), aprovação, inferência, redução diante de HTTP 503, timeout e cancelamento. O [índice de evidências](evidences/sprint-05/README.md) relaciona imagens, IDs e resultados.

Os testes do motor usam um alvo HTTP local descartável; nenhuma carga automatizada é enviada a serviços externos. Os testes de IA geram artefatos temporários fora do repositório.

## Bugs encontrados e correções

| Problema observado | Correção aplicada |
|---|---|
| Requisições rápidas podiam deixar o motor praticamente serial. | Criados trabalhadores de longa duração, um por vaga de concorrência, mantendo a quantidade configurada em voo. |
| O corpo inteiro da resposta podia ser mantido em memória. | Uso de resposta em streaming; apenas status e tempo são necessários. |
| A janela cancelada gravava duração planejada. | Persistência do tempo efetivamente observado, corrigindo throughput. |
| O ramp-up era lido do cenário mutável. | Inclusão no snapshot de `test_executions`. |
| Cenários não possuíam teto operacional. | Limites na API e constraints correspondentes no banco. |
| `RULES` e `AI_HYBRID` usavam progressão fixa. | Integração do controlador e do preditor ao laço entre janelas. |
| Artefato poderia ser trocado após o treino. | Verificação de SHA-256 e esquema antes da desserialização. |
| Frontend terminava em projetos e endpoints. | Painel funcional do fluxo adaptativo e administração de modelos. |
| Duração da janela truncada no intervalo nominal, apesar de requisições em voo. | Registro do tempo real e orçamento da execução pelo relógio monotônico. |
| Pool HTTP limitava a concorrência a 100 mesmo com configuração maior. | Pool dimensionado pelo teto do cenário; teste local com 110 vagas. |
| Falha de banco podia entrar no bloco de fallback de inferência. | Captura restrita ao preditor; falha SQL encerra a execução com diagnóstico sanitizado. |
| Listagem atrasada sobrescrevia a execução do cenário recém-selecionado. | Identificação das consultas e invalidação das respostas antigas. |
| Base histórica incompatível falhava somente ao criar as constraints. | Pré-verificação transacional com contagens e abortamento antes das alterações. |
| Novas consultas do monitor invalidavam continuamente respostas lentas. | Polling sequencial, reagendado depois da conclusão da consulta anterior. |
| Metadados tratavam cinco janelas variáveis como dez segundos fixos. | Contrato explicitado em janelas, duração nominal e extremos reais registrados; timestamps no fim da observação. |

O horizonte é de cinco janelas futuras, nominalmente dez segundos. Janelas que drenam requisições lentas podem durar mais; os metadados novos registram essa variação. Não há garantia de previsão em exatamente dez segundos. O teste de regressão com janelas de quatro segundos confirma um horizonte observado de vinte segundos, sem rotulá-lo como dez.

## Segurança e pendências

A revisão do histórico Git não encontrou chaves privadas, tokens ou credenciais preenchidas. `.env`, artefatos `joblib`, chaves e credenciais continuam ignorados; somente `.env.example` é versionado. O `npm audit` do lockfile não registrou vulnerabilidades conhecidas na data da análise.

Evoluções operacionais registradas:

- definir política de saída de rede/allowlist antes de implantação compartilhada, pois o produto acessa URLs informadas pelo QA;
- reconciliar execuções `RUNNING` após reinicialização inesperada da API;
- consolidar relatórios comparativos entre as três estratégias;

A reprodutibilidade das dependências Python foi implementada com `uv.lock` e exportação com hashes consumida pelo Dockerfile; a imagem foi construída no laboratório. Os avisos de depreciação de Starlette/httpx e da configuração de caminhos do Alembic foram registrados sem falhas. Esses testes não substituem uma auditoria periódica das dependências.

## Dificuldades e próximos passos

A disponibilidade do Docker foi necessária para superar o bloqueio de ambiente e validar o banco e o build completos. O conjunto de aprendizado precisou conter períodos saudáveis e degradados nas três partições, motivando uma coleta temporal mais longa. A próxima etapa consolida ensaios repetidos e comparáveis entre FIXED, RULES e AI_HYBRID, além das melhorias operacionais acima.

## Referências técnicas

- `backend/app/modules/intelligence/dataset.py` — características, horizonte e hash do conjunto;
- `backend/app/modules/intelligence/training.py` — treino, comparação, métricas e aprovação;
- `backend/app/modules/intelligence/predictor.py` — validação e inferência local;
- `backend/app/modules/load_tests/engine.py` — carga, integração adaptativa e fallback;
- `backend/app/modules/intelligence/api.py` — rotas de modelos, previsões e decisões;
- `backend/migrations/versions/20261001_0003_sprint05_intelligence_metadata.py` — evolução do banco;
- `frontend/src/SprintFivePanel.tsx` — fluxo demonstrável na interface;
- `database/schema.sql` e `docs/diagrams/relational-model.mmd` — modelo relacional atualizado;
- `docs/analise-pre-sprint-05.md` — diagnóstico anterior à implementação.

## Conclusão

A Sprint 05 implementa o segundo módulo integrado ao banco e ao motor de carga. Os testes e o experimento controlado demonstram treinamento, inferência, persistência, recuperação e decisões por janela. A interface permite executar o fluxo de cenário, carga, monitoramento e parada com dados reais. A comparação de desempenho entre estratégias e a preparação para implantação compartilhada são os próximos passos.
