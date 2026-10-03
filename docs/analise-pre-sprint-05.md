# Análise técnica anterior à Sprint 05

## Identificação da revisão

- **Repositório:** `camimcl/sre-fabrica-de-software`
- **Branch analisada:** `main`
- **Revisão sincronizada:** `54ecca4bea804deb65aaf361641ce7a4c196a262`
- **Data da análise:** 1 de outubro de 2026
- **Escopo:** backend, frontend, banco, migrations, testes, configuração local, histórico Git e documentação até a Sprint 04.

Esta revisão confirma que o LoadForge já possui a base operacional e o primeiro módulo funcional, mas ainda não executa o ciclo de inteligência e controle adaptativo descrito na arquitetura. A Sprint 05 deve transformar os contratos existentes de `intelligence` e `control` em um segundo módulo completo, persistido e integrado ao motor de carga.

## Estado implementado

| Área | Situação observada | Evidência principal |
|---|---|---|
| Ambiente local | Banco, API e frontend são orquestrados por Docker Compose, com credenciais obrigatórias e portas limitadas ao computador local. | `docker-compose.yml` |
| Autenticação e perfis | Cadastro, login, sessão, perfis QA e Visualizador e regras administrativas estão implementados. | `backend/app/modules/auth/` |
| Projetos e endpoints | CRUD persistido, propriedade do projeto e confirmação de autorização do alvo estão implementados. | `backend/app/modules/projects/` |
| Testes de carga | Cenários, execuções, máquina de estados, motor HTTP assíncrono, cancelamento e janelas de métricas estão implementados. | `backend/app/modules/load_tests/` e `backend/app/modules/metrics/` |
| Frontend | A interface cobre autenticação, usuários, projetos e endpoints. As telas de cenário, execução e monitoramento ainda não consomem o módulo da Sprint 04. | `frontend/src/App.tsx` |
| Inteligência local | Há contratos e tabelas para versões e previsões, mas não há preparação de dados, treinamento, carregamento de artefato, inferência ou API. | `backend/app/modules/intelligence/contracts.py` e `models.py` |
| Controle adaptativo | O controlador determinístico existe isoladamente, mas não é chamado pelo motor e as decisões não são persistidas. | `backend/app/modules/control/contracts.py` e `models.py` |
| Relatórios | Existe apenas o modelo relacional; não há consolidação ou rota de relatório. | `backend/app/modules/reports/models.py` |

O relatório da Sprint 04 registra explicitamente o `load_tests` como primeiro módulo completo e indica a previsão local de risco e o controlador adaptativo como próximos passos. Essa continuidade também corresponde ao ciclo `métricas -> IA local -> controle -> nova concorrência` definido no ADR 002 e no diagrama de arquitetura.

## Resultado das verificações

### Backend

A suíte completa executou com **44 testes aprovados e 2 testes ignorados**. Os testes ignorados dependem de `LOADFORGE_TEST_DATABASE_URL` e de um PostgreSQL descartável cujo nome termine em `_test`. Não houve falha funcional na suíte executável em SQLite.

### Frontend

A verificação TypeScript (`tsc -b`) foi concluída sem erros. O empacotamento Vite não pôde ser finalizado neste ambiente de análise porque a execução de um subprocesso do empacotador foi bloqueada pelo Windows com `EPERM`; a falha ocorreu na ferramenta de construção, antes da compilação da aplicação, e não caracteriza defeito confirmado no código-fonte.

### Dependências e segredos

- O `npm audit` do lockfile registrou **zero vulnerabilidades** nas dependências do frontend.
- As versões resolvidas das dependências diretas do backend não apresentaram avisos de vulnerabilidade em seus metadados oficiais do PyPI na data da análise.
- A busca por padrões de tokens, chaves privadas e credenciais em **33 revisões Git** não encontrou correspondências. O único arquivo de ambiente presente no histórico é `.env.example`, sem segredos preenchidos.
- O backend não possui lockfile com versões e hashes exatos. As faixas de versão em `pyproject.toml` permitem que duas instalações em datas diferentes resolvam conjuntos distintos de dependências. Trata-se de uma pendência de reprodutibilidade e cadeia de suprimentos.

## Bugs e riscos identificados

| Prioridade | Item | Impacto | Referência |
|---|---|---|---|
| Alta | O motor ainda calcula a concorrência por uma progressão fixa e não consulta `RulesController`, `RiskPredictor` ou `AdaptiveLoadController`. | As estratégias `RULES` e `AI_HYBRID` não mudam o comportamento real da execução. | `backend/app/modules/load_tests/engine.py`, função `_concurrency_for_window` |
| Alta | A rotina de uma janela adiciona tarefas gradualmente e pode operar quase de forma serial quando o alvo responde rapidamente. | A concorrência configurada pode não ser efetivamente mantida e as métricas deixam de representar a carga solicitada. | `backend/app/modules/load_tests/engine.py`, função `_run_window` |
| Alta | `duration_seconds`, `max_concurrency` e `timeout_ms` possuem mínimo, mas não possuem teto na validação da API. | Uma conta QA pode configurar consumo excessivo de CPU, conexões e tempo no mesmo processo da API. | `backend/app/modules/load_tests/schemas.py`, classe `ScenarioWrite` |
| Média | A execução copia parte da configuração do cenário, porém lê `ramp_up_per_window` do cenário atual ao iniciar. | Alterar o cenário após criar a execução muda silenciosamente um parâmetro do teste histórico. | `backend/app/modules/load_tests/api.py`, `_SNAPSHOT_FIELDS`; `engine.py`, `_load_plan` |
| Média | O cancelamento no meio da janela persiste a duração planejada, não o tempo realmente observado. | O throughput da última janela cancelada pode ser subestimado. | `backend/app/modules/load_tests/engine.py`, `run_execution` |
| Média | Uma reinicialização da API perde o registro em memória das tarefas ativas. | Execuções podem permanecer em `RUNNING` sem motor associado após uma queda do processo. | `backend/app/modules/load_tests/engine.py`, `EngineRegistry` |
| Média | URLs autorizadas podem apontar para endereços internos acessíveis pela API. | Em implantação compartilhada, um QA comprometido pode usar o motor como origem de requisições à rede interna. | `backend/app/modules/projects/schemas.py`, `EndpointWrite` |
| Baixa | O frontend permanece em um único componente extenso e ainda identifica visualmente a Sprint 03. | A manutenção e a demonstração do módulo de carga ficam mais difíceis. | `frontend/src/App.tsx` |
| Baixa | O relatório da Sprint 04 registra 39 testes, enquanto o documento incremental registra 44. | A evidência documental fica inconsistente com a suíte atual. | `docs/relatorio-sprint-04.md` e `sprint4.docx` |

## Escopo recomendado para o segundo módulo

O segundo módulo será tratado como **inteligência local e controle adaptativo**, porque esses componentes formam uma única cadeia operacional e já compartilham contratos e entidades:

1. transformar janelas de métricas em características e rótulos reproduzíveis;
2. treinar localmente regressão logística e Random Forest, usando separação temporal;
3. selecionar e versionar o melhor candidato por métricas objetivas;
4. aprovar uma versão e carregá-la sem serviço externo;
5. inferir risco durante execuções `AI_HYBRID`;
6. aplicar o controlador por regras em `RULES` e como fallback seguro em `AI_HYBRID`;
7. persistir previsões e decisões por janela;
8. oferecer rotas para treinar, aprovar e consultar modelos, previsões e decisões;
9. integrar a experiência mínima no frontend para que o fluxo seja demonstrável;
10. corrigir os bugs do motor que afetam concorrência, limites e rastreabilidade.

## Critérios técnicos para a Sprint 05

- Uma execução `RULES` deve alterar a concorrência conforme limites observados e registrar cada decisão.
- Uma execução `AI_HYBRID` deve usar a versão aprovada, persistir a previsão e registrar a decisão aplicada.
- Na ausência ou falha do modelo, a execução deve continuar pelo fallback de regras e registrar o motivo.
- Versões de modelo devem ser consultáveis e possuir estado controlado (`CANDIDATE`, `APPROVED` ou `RETIRED`).
- O treinamento deve rejeitar conjunto insuficiente, evitar divisão aleatória entre janelas futuras e registrar hash e métricas do conjunto utilizado.
- As migrations, o esquema SQL e os modelos SQLAlchemy devem permanecer equivalentes.
- Testes unitários, de API, persistência e fluxo integrado devem demonstrar os caminhos normal, fallback e erro.

## Referências de base

- `docs/relatorio-sprint-04.md`
- `docs/architecture/decisions/ADR-002-local-ai-and-fallback.md`
- `docs/diagrams/architecture.mmd`
- `backend/app/modules/load_tests/engine.py`
- `backend/app/modules/intelligence/`
- `backend/app/modules/control/`
- `frontend/src/App.tsx`
