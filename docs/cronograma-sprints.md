# Cronograma oficial revisado do LoadForge

**Revisão:** 13/11/2026
**Motivo:** registrar as entregas integradas das Sprints 06 e 07 e a consolidação funcional, de permissões e usabilidade da Sprint 08. A revisão de 15/10 antecipou formalmente a IA e o controlador, conforme descrito abaixo.

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
| 06 | Terceiro módulo: histórico, relatórios e avaliação experimental | Implementada e integrada | Relatórios por execução, comparação repetida entre `FIXED`, `RULES` e `AI_HYBRID`, dispersão e condições auditáveis; ganho experimental não presumido |
| 07 | Dashboard, relatórios, pesquisas, filtros, exportação e auditoria | Implementada e integrada (PR 6) | Indicadores e consultas com dados persistidos, CSV/PDF e histórico de operações |
| 08 | Consolidação funcional, permissões, usabilidade e regras de negócio | Implementada e integrada (PR 7) | Gestão completa de cenários, exportações integradas, matriz de acesso testada, validação de autorização, proteção do último QA e evidências automatizadas |
| 09 | Regressão integrada e correções de estabilidade | Integrada na base `cc9984f` | 167 testes backend, 11 frontend, percurso e persistência registrados no relatório histórico |
| 10 | Release Candidate 1.0.0-rc.1 | Validada localmente e publicada para revisão, sem merge | 187 testes backend, 14 frontend, sete verificações integradas, recuperação real, banco conferido, OpenAPI e README atualizados; PRs #22 a #28 |

## Critérios experimentais da Sprint 06

- utilizar as mesmas condições de duração, concorrência, ramp-up, timeout, limites e endpoint para as três estratégias;
- exigir ao menos três repetições concluídas por estratégia em cada comparação;
- registrar média e desvio-padrão de throughput, latência p95 e taxa de erro;
- registrar volume de requisições, sucessos, timeouts, pico de concorrência e violações de limite;
- manter o conjunto de teste do modelo separado da calibração do limiar;
- tratar recall `0,80` como requisito de aprovação de novos modelos, sem apagar nem reinterpretar o resultado histórico de `0,70370`;
- apresentar ganhos e perdas por métrica, sem declarar uma estratégia vencedora quando as evidências forem inconclusivas.

## Rastreabilidade

O escopo da Sprint 08 segue os quatro critérios da entrega solicitada. A validação
externa e a campanha experimental ampliada permanecem próximas atividades de
validação; não são declaradas concluídas apenas pela implementação dos módulos.
Não houve retirada de funcionalidades do MVP nesta revisão. A restrição a Python
3.11/3.12 foi explicitada por compatibilidade com o conjunto científico fixado;
suportar versões mais novas requer atualizar e revalidar esse conjunto.

Consulte o [relatório da Sprint 08](relatorio-sprint-08.md) para a matriz de
funcionalidades, permissões, testes e limites desta entrega.

Este arquivo é a fonte formal do cronograma revisado. Os relatórios de cada sprint registram a execução real, e qualquer nova mudança de escopo deve atualizar este cronograma no mesmo commit da decisão.

## Sprint 10 - consolidação da RC

A entrega consolida os módulos já implementados e não remove funcionalidades do
MVP. A revisão acrescenta encerramento/recuperação do motor, posse exclusiva da
API por banco, validação do esquema, documentação de todas as operações e revisão
de apresentação. Não altera o esquema migrado nem aprova modelos ou declara
ganho experimental sem evidência. Consulte o [plano](plano-sprint-10.md), o
[guia de operação](release-candidate.md) e o [relatório](relatorio-sprint-10.md).

## Sprint 09 - prazo 07/11/2026

Verificação registrada em 06/11: 167 testes backend, 11 frontend, 17 verificações integradas e dois retestes de concorrência de interface aprovados; quatro defeitos corrigidos, documentação atualizada e entrega incremental. Alterações organizadas localmente por tarefa. Consulte [relatório](relatorio-sprint-09.md) e [divisão](plano-sprint-09.md).
