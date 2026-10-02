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

A migration `20261001_0003` adiciona o snapshot e os metadados auditáveis. A migration `20261001_0004` e o esquema SQL acrescentam um índice único parcial para impedir dois modelos aprovados simultaneamente. Ao migrar duplicatas históricas, a versão aprovada mais recente é preservada e as demais são aposentadas. A API desfaz a transação e retorna conflito quando aprovações concorrentes disputam essa restrição. A aplicação das migrations em PostgreSQL ainda precisa ser validada. Os artefatos locais são mantidos no volume Docker `loadforge_model_artifacts`; o banco guarda o caminho relativo e o SHA-256 esperado.

## Regras de negócio atualizadas

| Regra | Decisão e justificativa |
|---|---|
| Horizonte preditivo | Cinco janelas de dois segundos, preservando o objetivo de antecipar degradação em dez segundos. |
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
| Backend completo | **55 aprovados, 2 ignorados** | Autenticação, persistência, motor, limites, IA, controle, APIs e segurança; repetidos com dependências do lockfile. |
| Pipeline de IA | Aprovado | Horizonte temporal, treinamento, seleção, aprovação, inferência e rejeição de artefato adulterado. |
| Controle integrado | Aprovado | Decisão por regras, previsão híbrida, persistência e fallback sem modelo. |
| Motor de carga | Aprovado | Concorrência efetiva, erros, timeout, cancelamento e duração observada. |
| TypeScript | Aprovado | Compilação estática das telas existentes e do painel da Sprint 05. |
| Dependências Python | Aprovado no Windows com Python 3.11 | Ambiente novo instalado a partir do lockfile; 44 pacotes compatíveis; suíte concluída em 38,37 s. |
| Build de produção e navegador | Pendente | A instalação npm falhou com `spawn EPERM`; a verificação TypeScript em cópia local não substitui o build nem o teste visual. |
| Docker Compose | Configuração válida | Interpolação validada com valores descartáveis; daemon Docker indisponível na máquina durante a verificação. |
| PostgreSQL real | Não executado nesta revisão | Dois testes permanecem condicionados a `LOADFORGE_TEST_DATABASE_URL` e banco `_test`. |

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

## Segurança e pendências

A revisão do histórico Git não encontrou chaves privadas, tokens ou credenciais preenchidas. `.env`, artefatos `joblib`, chaves e credenciais continuam ignorados; somente `.env.example` é versionado. O `npm audit` do lockfile não registrou vulnerabilidades conhecidas na data da análise.

Pendências antes da conclusão da revisão:

- executar os dois testes de integração em um PostgreSQL descartável quando o daemon Docker estiver disponível;
- definir política de saída de rede/allowlist antes de implantação compartilhada, pois o produto acessa URLs informadas pelo QA;
- reconciliar execuções `RUNNING` após reinicialização inesperada da API;
- consolidar relatórios comparativos entre as três estratégias;
- separar falhas de persistência de falhas de inferência no motor;
- impedir respostas atrasadas após troca rápida de cenário/projeto;
- corrigir a duração observada de janelas com requisições que ultrapassam o intervalo e conferir o dimensionamento do pool HTTP;
- validar a migração de históricos fora dos novos limites, preservando os dados;
- concluir build de produção e navegação ponta a ponta.

A reprodutibilidade das dependências Python foi implementada com `uv.lock` e exportação com hashes consumida pelo Dockerfile. Isso não representa validação da imagem Docker, ainda indisponível neste ambiente, nem uma nova auditoria completa das dependências. O aviso de depreciação de Starlette/httpx continua registrado; não houve falha nos testes por esse aviso.

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

A Sprint 05 implementa os contratos de IA e controle como um segundo módulo integrado ao banco e ao motor de carga. Os testes locais demonstram treinamento, inferência, persistência e decisões por janela. A homologação completa em PostgreSQL e navegador permanece pendente, assim como as correções específicas listadas acima; a implementação não equivale ao aceite final.
