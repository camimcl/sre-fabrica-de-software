# Cronograma oficial revisado do LoadForge

**Revisão:** 15/10/2026
**Motivo:** incorporar formalmente a antecipação da inteligência local e do controlador adaptativo e reposicionar a avaliação experimental e os relatórios comparativos.

## Mudança de planejamento

O planejamento inicial tratava inteligência, controle adaptativo e comparação experimental como uma sequência posterior ao motor de carga. A Sprint 05 antecipou e concluiu a cadeia operacional `métricas → previsão local → decisão → nova concorrência`, incluindo fallback por regras, persistência, interface e testes.

Essa antecipação não elimina a etapa experimental. Ela desloca para a Sprint 06 a obrigação de medir o resultado em ensaios equivalentes e repetidos, registrar limitações e disponibilizar os resultados no terceiro módulo do produto.

## Cronograma revisado

| Sprint | Módulo ou entrega | Estado | Evidência esperada |
|---|---|---|---|
| 01 | Descoberta, problema, escopo e organização | Concluída | Visão do produto e backlog inicial |
| 02 | Arquitetura, dados, protótipos e contratos | Concluída | Diagramas, modelo relacional e fluxo de referência |
| 03 | Base operacional: autenticação, usuários, projetos e endpoints | Concluída | Fluxo persistido com perfis QA e Visualizador |
| 04 | Primeiro módulo: cenários, execuções e motor de carga | Concluída | Geração real de carga, métricas e parada emergencial |
| 05 | Segundo módulo antecipado: inteligência local e controle adaptativo | Concluída | Treino, aprovação, inferência, decisões, fallback e interface integrada |
| 06 | Terceiro módulo: histórico, relatórios e avaliação experimental | Em execução | Relatórios por execução, comparação repetida entre `FIXED`, `RULES` e `AI_HYBRID`, dispersão dos resultados, interface e navegação revisadas |
| 07 | Consolidação, segurança operacional e validação externa | Planejada | Correções da Pré-Banca, capacidade, recuperação e documentação final |
| 08 | Entrega final e demonstração | Planejada | Evidências reproduzíveis, apresentação e pacote final |

## Critérios experimentais da Sprint 06

- utilizar as mesmas condições de duração, concorrência, ramp-up, timeout, limites e endpoint para as três estratégias;
- exigir ao menos três repetições concluídas por estratégia em cada comparação;
- registrar média e desvio-padrão de throughput, latência p95 e taxa de erro;
- registrar volume de requisições, sucessos, timeouts, pico de concorrência e violações de limite;
- manter o conjunto de teste do modelo separado da calibração do limiar;
- tratar recall `0,80` como requisito de aprovação de novos modelos, sem apagar nem reinterpretar o resultado histórico de `0,70370`;
- apresentar ganhos e perdas por métrica, sem declarar uma estratégia vencedora quando as evidências forem inconclusivas.

## Rastreabilidade

Este arquivo é a fonte formal do cronograma revisado. Os relatórios de cada sprint registram a execução real, e qualquer nova mudança de escopo deve atualizar este cronograma no mesmo commit da decisão.
