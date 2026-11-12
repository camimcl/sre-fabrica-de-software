# Relatório técnico - Sprint 09

Grupo 21 - LoadForge | CC8NB | 06/11/2026 | Prazo: 07/11/2026.
Registro de QA/PO: Camile Marcele Pereira de Araújo. Base analisada: main `f9a62fb` (PR 7, Sprint 08).

## 1. Análise do estado e divisão da entrega

Analisei os módulos existentes e organizei a verificação por risco. A aplicação já reúne autenticação, gestão de usuários/projetos/endpoints, cenários, motor HTTP, IA local, controle, relatórios, consultas, dashboard e auditoria. A Sprint 09 acrescenta cobertura, corrige quatro defeitos e alinha a documentação. O plano e a divisão de responsabilidades estão em [plano-sprint-09.md](plano-sprint-09.md). Os testes aqui descritos foram executados por automação; as capturas são da aplicação real.

| Responsabilidade | Integrantes de referência | Material para revisão/apresentação |
|---|---|---|
| QA/PO | Camile | Matriz, reprodução, retestes, evidências e roteiro |
| Backend | Aline e Emerson | Validação de autorização, contratos e motor |
| Banco/infraestrutura | Ricardo | Laboratório isolado, persistência e modelos |
| Frontend | Cayo | Navegação, contexto e mensagens |
| Coordenação/envio único | Emerson | Consolidação e apresentação da equipe |

A divisão orienta revisão e apresentação; os resultados automatizados não são atribuídos como execução manual individual.

## 2. Ambiente e resultados

Laboratório Docker próprio: PostgreSQL 16, Python 3.11, API FastAPI e frontend React/Nginx. Banco de demonstração e banco `_test` separados, credenciais geradas localmente e alvo HTTP pertencente ao laboratório. Edge headless, viewport 1280x960 e fuso America/Fortaleza no percurso principal. As datas brutas das evidências estão em UTC; 07/11 às 01h UTC corresponde a 06/11 às 22h em Fortaleza.

| Verificação | Esperado | Obtido |
|---|---|---|
| Regressão backend com PostgreSQL | Todos aprovados; nenhum skip | 167 aprovados, zero falhas/ignorados, 91,64 s; oito avisos |
| Frontend | Mensagens/filtros/downloads preservados | 11 aprovados, zero falhas/ignorados |
| Percurso integrado | Cadastros até relatórios com dados reais | 17 verificações aprovadas |
| Resposta atrasada entre projetos | Não misturar lista/rascunho | NAV-RACE-01 aprovado |
| Datas inválidas durante consulta | Encerrar carregamento e recuperar após limpar | NAV-RACE-02 aprovado |
| Persistência após reinício da API | Recuperar projeto, execuções e comparação | 11 execuções e uma comparação recuperadas |
| Build | Imagens compiladas e serviços saudáveis | TypeScript/Vite e imagens API/frontend concluídos |

A regressão backend final refere-se à revisão funcional `7c2c87c`. Documentação e o script de comprovação de persistência foram adicionados depois. A rodada inicial de 153 casos teve 152 aprovados e uma falha de preparação SQLite; o reteste corrigiu o contexto, sem ocultar a ocorrência.

## 3. Casos, procedimentos e rastreabilidade

Os 167 nomes, durações e resultados individuais estão em [casos-backend.csv](evidences/sprint-09/casos-backend.csv) e no [JUnit](evidences/sprint-09/pytest-final.xml). O CSV de [navegação](evidences/sprint-09/casos-navegacao.csv) registra esperado e obtido por caso. O XML é a evidência primária do executor, não uma contagem elaborada manualmente.

| Grupo | Procedimento e resultado esperado | Resultado obtido / referência |
|---|---|---|
| Autenticação e contas | Cadastro público VIEWER; login inválido 401; perfil obrigatório; CRUD QA e proteção do último QA | Testes test_api, auth_security, sprint08_permissions/concurrency aprovados; NAV-01/09/10 |
| Projetos/endpoints | Criar, consultar, editar e excluir; propriedade; dependências 409 | test_api e 28 validações S09 aprovados; NAV-02 e VAL-API-01 |
| Validação HTTP | Limites, nome em branco, URL inválida, credenciais na URL, método TRACE e campo extra | 422 explicado, estado anterior preservado; test_sprint09_validation |
| Autorização | Textos/números não confirmam autorização; true/false seguem fluxo explícito | 14 casos aprovados; test_sprint09_authorization |
| Cenário/execução | Limites e snapshot; iniciar com confirmação; métricas reais; cancelar; estados inválidos | test_load_tests_api/integration, test_load_engine; NAV-03/06 |
| IA/controle | Pipeline temporal, aprovação por recall, hash, inferência, falha e fallback | test_intelligence e test_control_contract aprovados; treinamento insuficiente informado em NAV-04 |
| Relatórios | Relatório individual; comparação 3x3 equivalente; CSV/PDF válidos | test_reports; NAV-05, FUNC-HTTP-01 |
| Consultas/auditoria | Filtros, paginação, período, logs transacionais e exportações | test_sprint07, test_query_utils; NAV-07/08 |
| Navegação/perfis | Visualizador e QA não proprietário consultam sem escrita; API 403 | NAV-11/12; testes de permissão aprovados |

## 4. Evidências explicadas

O [índice de evidências](evidences/sprint-09/README.md) associa capturas a procedimentos. Em NAV-03 cadastrei um cenário pela tela, confirmei a autorização e iniciei o motor; o estado COMPLETED e as métricas foram recuperados pela API. Em NAV-06 executei a parada e confirmei CANCELLED persistido. Em FUNC-HTTP-01 executei três repetições de cada estratégia contra o mesmo alvo e gerei a comparação. Sem modelo aprovado, AI_HYBRID utilizou regras; a conclusão do relatório mantém essa limitação. Em NAV-05 e NAV-07 os downloads foram salvos e os PDFs tiveram a assinatura `%PDF-` conferida; o CSV filtrado continha FIXED e não continha AI_HYBRID.

No teste de persistência consultei por SQL as tabelas e a revisão Alembic `20261020_0007`, encerrei a conexão, reiniciei apenas a API e fiz novo login. O projeto recuperou 11 execuções (10 concluídas e uma cancelada), cinco cenários, um endpoint e uma comparação. As contagens globais do laboratório incluem execuções exploratórias anteriores e estão identificadas separadamente em persistence.json. Isso não é restore de backup nem teste de recuperação de execução em andamento.

## 5. Bugs e regras atualizadas

O [registro de bugs](bugs-sprint-09.md) detalha severidade, reprodução, esperado/obtido, causa, correção e reteste. Corrigi a aceitação implícita de consentimento, o erro de mensagem para JSON null, a resposta atrasada entre projetos e o carregamento preso com datas inválidas. A confirmação do alvo agora exige booleano JSON; não houve mudança de tabelas nem retirada de funcionalidade. Proteções de propriedade, perfis, aprovação de modelo e dependências continuam ativas.

## 6. Documentação e arquitetura

Atualizei README, cronograma, guia de contribuição, arquitetura, fontes de classes/MER/relacional e exportações atuais por domínio. Os 13 modelos incluem operation_logs; actor_id é opcional com SET NULL e entity_id é polimórfico. Corrigi cardinalidades opcionais e a descrição do horizonte como cinco janelas futuras. O desenho histórico permanece identificado como planejamento; as novas imagens refletem as colunas ORM. Fontes: [diagramas](diagrams/README.md), [arquitetura](architecture/README.md) e schema.sql. As páginas 1-81 do documento incremental são preservadas integralmente; a Sprint 09 começa na página 82, seção 67.

## 7. Segurança, dificuldades e próximos passos

As credenciais ficam em `.qa-local/`, ignorada pelo Git, e não integram os arquivos de evidência. Não foram usados alvos externos de carga. A revisão desta sprint cobre validação, acesso, integridade e tratamento de erros; não substitui pentest nem afirma ausência absoluta de vulnerabilidades. A autorização coercível foi endurecida como regra de segurança, sem exploração externa demonstrada.

As dificuldades foram a inicialização do Docker, uma porta indisponível no Windows, alinhamento do contexto SQLite e reprodução determinística de respostas atrasadas. Permanecem oito avisos de depreciação, ampliação experimental com modelo aprovado, recall/antecipação em teste reservado e verificação de usabilidade em outras resoluções. O motor no processo da API exige planejamento de recuperação para uma futura versão mais resiliente.

O fluxo novo é uma branch por tarefa com commits coerentes e dependências explícitas, descrito em CONTRIBUTING.md. As alterações desta entrega estão locais para revisão; publicação e PRs são uma etapa posterior. Repositório: https://github.com/camimcl/sre-fabrica-de-software . Protótipo: https://www.figma.com/design/isw6HZdCiomQvSekNScl9J . O protótipo é uma referência sujeita à evolução; as evidências desta sprint mostram a interface implementada.
