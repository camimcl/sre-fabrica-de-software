# Evidências da Release Candidate - Sprint 10

Verificação local em 13/11/2026. Código backend identificado pelo hash da árvore
em `results.json`; percurso integrado executado sobre a revisão `c8d5087`.
Os commits seguintes fecham documentação/evidências, sem mudar a implementação.

| Evidência | Resultado |
|---|---|
| [results.json](results.json) | Resumo de testes, build, esquema e limites |
| [pytest.xml](pytest.xml) | 187 casos aprovados, sem falhas, erros ou skips; removido apenas o nome do computador |
| [frontend-tests.txt](frontend-tests.txt) | 14 testes frontend aprovados |
| [frontend-build.txt](frontend-build.txt) | TypeScript e build de produção Vite concluídos |
| [database.json](database.json) | CLI executada no contêiner final: head `20261020_0007`, 13 tabelas, 33 CHECKs esperadas, nenhuma divergência |
| [rc-smoke.json](rc-smoke.json) | Sete verificações HTTP/contêiner aprovadas, com identificadores dos dados reais criados |
| [consultas-rc.jpg](consultas-rc.jpg) | Interface reconstruída, pesquisa e filtros combinados retornando três execuções fixas concluídas; metadados e controles PDF revisados |
| [recuperacao-rc.jpg](recuperacao-rc.jpg) | Execução marcada como falha após SIGKILL, motivo visível e janela de métricas preservada |
| [SHA256SUMS.txt](SHA256SUMS.txt) | Integridade dos arquivos desta pasta; não constitui assinatura digital |

O percurso usa o laboratório isolado de `scripts/qa`, PostgreSQL 16, API FastAPI,
interface React e alvo `http://target:8080` próprio. Criou três repetições de
FIXED, RULES e AI_HYBRID, gerou relatórios e comparação, verificou os avisos,
consultas, filtros, CSV/PDF e negações de acesso do Visualizador. Conferiu
reinício normal com estado CANCELLED e queda abrupta com estado FAILED,
auditoria, métricas/comparação preservadas e ausência de replay de tráfego.

Após a queda, o teste observa novamente as métricas depois de 2,5 segundos para
confirmar que não continuaram crescendo. Os testes unitários também verificam
idempotência e recusa de um segundo runtime no mesmo banco. Não há teste de
alta disponibilidade: a arquitetura suporta uma API/worker por banco.

A largura 320/360 foi conferida no dashboard sem overflow horizontal; isso não
equivale a certificação de acessibilidade ou teste de todos os dispositivos.
As capturas são reais e não foram reconstruídas. Credenciais/tokens permanecem
fora dos resultados publicados. Um aviso de compatibilidade de TestClient/httpx
continua documentado no relatório técnico.

Esta comparação curta comprova funcionamento. Como não havia modelo aprovado
no laboratório, a estratégia híbrida utilizou fallback. Não se declara ganho
exclusivo de IA, significância estatística ou desempenho de produção.
CI remoto, deploy e ensaio de restauração em infraestrutura final não foram
executados. A primeira tentativa foi afetada por disco cheio; os resultados
desta pasta correspondem às verificações repetidas e aprovadas.
