# Evidências da Sprint 06

Data da verificação local: 16/10/2026, após rebase sobre o merge do PR #4.

## Evidências reproduzíveis já disponíveis

| Verificação | Resultado |
|---|---|
| Backend | [Relatório JUnit local](pytest-local.xml): 65 testes aprovados, zero falhas e 5 ignorados por ausência de PostgreSQL descartável configurado. |
| Frontend | TypeScript e build Vite de produção aprovados. |
| Dependências frontend | `source-map-js` atualizado de `1.2.1` para `1.2.2`; auditoria npm final com zero vulnerabilidades conhecidas. |
| Comparação | Fixture automatizada com 3 estratégias × 3 repetições valida equivalência, dispersão, deltas e persistência. |
| API integrada | Login de QA, criação da comparação, histórico com relatórios e recuperação do resultado aprovados. |
| Migração | O teste PostgreSQL existente passa a exigir a revisão `20261015_0005` e as duas novas tabelas quando o banco de teste é disponibilizado. |
| Compatibilidade com CI | `uv.lock` alinhado à versão `0.6.0`; `uv sync --locked`, `uv lock --check` e o comando pytest do workflow aprovados localmente. |

Os dados numéricos da fixture são deliberadamente controlados para testar os cálculos. Eles não demonstram que a IA superou as demais estratégias em uma carga real.

## Evidência experimental a coletar

A sessão de laboratório deve produzir uma comparação persistida com no mínimo nove execuções reais e registrar:

- identificador da comparação e das execuções;
- versão do alvo autorizado e condições do ambiente;
- ordem das repetições;
- médias, desvios-padrão, mínimos e máximos;
- deltas de `AI_HYBRID` contra `FIXED` e `RULES`;
- incidentes, aquecimento e repetições descartadas com justificativa;
- captura da tela antes e depois de recarregar a aplicação.

O procedimento completo está no [Relatório Técnico da Sprint 06](../../relatorio-sprint-06.md). O repositório mantém a lacuna identificada até a execução real, em vez de promover números sintéticos como evidência de desempenho.
