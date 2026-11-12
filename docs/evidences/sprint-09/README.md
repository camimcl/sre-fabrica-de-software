# Evidências - Sprint 09

Capturas de aplicação real em Edge, API Docker e PostgreSQL 16. Datas brutas UTC; registro da entrega em 06/11/2026, Fortaleza. Credenciais e tokens foram excluídos.

| Arquivo | Procedimento / resultado demonstrado |
|---|---|
| [01-cadastro-persistido.png](01-cadastro-persistido.png) | NAV-02/VAL-UI-01: projeto atualizado e alvo autorizado persistidos. |
| [02-validacao-concorrencia.png](02-validacao-concorrencia.png) | VAL-UI-02: inicial 3 > máxima 2; botão Salvar cenário desabilitado. |
| [03-execucao-metricas.png](03-execucao-metricas.png) | NAV-03: execução COMPLETED e janela com requisições reais. |
| [04-validacao-treinamento.png](04-validacao-treinamento.png) | NAV-04: insuficiência de dados de treino informada. |
| [05-parada-emergencial.png](05-parada-emergencial.png) | NAV-06: parada efetiva e estado CANCELLED. |
| [06-comparacao.png](06-comparacao.png) | FUNC-HTTP-01: nove execuções e comparação; fallback explicitado. |
| [07-dashboard.png](07-dashboard.png) | NAV-07: indicadores recuperados do banco. |
| [08-validacao-periodo.png](08-validacao-periodo.png) | NAV-07: datas invertidas e exportação desabilitada. |
| [09-consulta-filtrada.png](09-consulta-filtrada.png) | NAV-07: três execuções FIXED recuperadas pelo filtro. |
| [10-auditoria.png](10-auditoria.png) | NAV-08: detalhes de operação expandidos. |
| [11-usuarios.png](11-usuarios.png) | NAV-09: nome de usuário atualizado pela interface. |
| [12-visualizador.png](12-visualizador.png) | NAV-11: dashboard de consulta sem auditoria global. |
| [race-before.png](race-before.png) | S09-B03 antes: endpoint A mostrado em projeto B. |
| [race-after.png](race-after.png) | S09-B03 depois: projeto B conserva rascunho e lista correta. |
| [dashboard-before.png](dashboard-before.png) | S09-B04 antes: intervalo inválido com carregamento preso. |
| [dashboard-after.png](dashboard-after.png) | S09-B04 depois: validação sem carregamento preso. |

Resultados: results.json, casos-navegacao.csv e casos-backend.csv. Retestes: race-after.json e dashboard-after.json. Persistência: persistence.json. Build concluído na reconstrução final do laboratório. PDFs e CSV efetivamente baixados estão nesta pasta. Os hashes SHA-256 permitem conferir os arquivos; não constituem assinatura digital.
