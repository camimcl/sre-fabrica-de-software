# Projeto da Fundação Técnica da Sprint 02 do LoadForge

## 1 Objetivo

Esta especificação define a fundação técnica que será adicionada na Sprint 02 sem reescrever ou invalidar o planejamento entregue na Sprint 01. As entregas são: descrição da arquitetura, diagrama de classes, modelo conceitual do banco, modelo relacional, protótipos navegáveis das telas, estrutura inicial executável do PostgreSQL, repositório organizado e uma seção incremental da Sprint 02 no documento do projeto.

As decisões da Sprint 01 permanecem como referência: o MVP usa um motor assíncrono em Python, um modelo de risco de degradação treinado localmente, um controlador adaptativo, PostgreSQL e nenhuma API externa de IA. Chatbot, IA generativa, CUDA, aceleração por GPU, Celery, Redis, execução distribuída e cobrança multi-tenant permanecem fora do MVP.

## 2 Escopo e critérios de conclusão

A Sprint 02 estará concluída quando:

- o repositório possuir uma estrutura coerente de monorepo para backend, futuro frontend, banco, testes, diagramas e protótipos;
- o PostgreSQL puder ser iniciado localmente e o esquema inicial puder ser aplicado de forma reproduzível;
- o esquema representar usuários, projetos, endpoints, cenários, execuções, janelas de métricas, versões do modelo, previsões, decisões do controlador e relatórios finais;
- a arquitetura mostrar explicitamente como a inferência participa do controle durante a execução;
- o diagrama de classes contiver as principais interfaces, implementações, atributos, métodos e relacionamentos;
- os modelos conceitual e relacional estiverem coerentes com a migration do banco;
- as telas principais do produto estiverem representadas em um protótipo Figma legível e navegável;
- o documento da Sprint 02 explicar cada diagrama e protótipo e acrescentar o novo conteúdo depois da Sprint 01;
- comandos de validação confirmarem a integridade do banco e da estrutura do repositório.

A Sprint 02 não implementará autenticação, motor de carga, treinamento, inferência em tempo de execução ou frontend de produção. Suas interfaces e estruturas de dados serão definidas agora para permitir a implementação nas Sprints seguintes sem redesenhar a fundação.

## 3 Abordagem arquitetural

### 3.1 Organização geral

O LoadForge usará um monólito modular em um monorepo. A futura interface será construída em React e TypeScript. Uma aplicação FastAPI oferecerá a interface HTTP e coordenará os módulos do domínio. O PostgreSQL armazenará o estado persistente. O artefato do modelo será carregado de um armazenamento local versionado. O motor assíncrono de carga poderá chamar somente alvos cuja autorização esteja registrada.

Essa abordagem foi escolhida porque o MVP exige forte integração entre execução do teste, métricas, inferência e controle adaptativo. Separar essas responsabilidades em serviços implantáveis independentes antes de validar o fluxo acrescentaria falhas de rede, fila, implantação e observabilidade sem melhorar o resultado da Sprint 02.

### 3.2 Módulos e pontos de variação

O código será organizado nos seguintes módulos:

- `auth`: usuários, credenciais, papéis e verificações de acesso;
- `projects`: projetos e endpoints autorizados;
- `load_tests`: cenários, execuções, transições de estado e cancelamento de emergência;
- `metrics`: agregação e persistência de janelas de métricas de dois segundos;
- `intelligence`: preparação de características, metadados, carregamento do modelo e inferência de risco;
- `control`: estratégias de concorrência fixa, por regras e assistida por IA;
- `reports`: comparações e resumos para apresentação;
- `db`: conexão, sessões, metadados, migrations e transações.

A interface externa para inferência será pequena:

```python
class RiskPredictor(Protocol):
    def predict_risk(self, features: MetricFeatures) -> RiskPrediction: ...
```

Duas implementações atenderão essa interface: a futura `SklearnRiskPredictor` e uma `UnavailableModelPredictor` determinística, usada para testar o fallback. A interface do controlador receberá uma janela de métricas e uma previsão opcional e retornará uma decisão, sem alterar diretamente a execução. Assim, a decisão poderá ser testada e seu motivo será registrado antes dos efeitos externos.

### 3.3 Fluxo durante uma execução

1. O usuário QA seleciona um endpoint autorizado e cria um cenário de teste.
2. A API valida a autorização e os limites da execução.
3. O motor inicia a execução e emite observações.
4. O módulo de métricas agrega uma janela de dois segundos.
5. O módulo de inteligência monta o vetor de características e solicita uma previsão local.
6. O módulo de controle combina métricas, limites configurados e previsão.
7. O coordenador aplica o novo valor de concorrência.
8. Janela, previsão, decisão, versão do modelo e estado da execução são persistidos em sequência consistente.
9. O relatório compara execuções fixas, por regras e assistidas por IA.

Se o carregamento ou a inferência falhar, o sistema registrará a falha e transferirá o controle para a estratégia por regras. Uma falha de inferência não poderá encerrar o teste de carga.

## 4 Projeto do banco de dados

### 4.1 Entidades conceituais

- `User`: pessoa autenticada com papel QA ou Visualizador.
- `Project`: sistema autorizado organizado como projeto da equipe.
- `Endpoint`: alvo HTTP pertencente a um projeto e acompanhado de evidência de autorização.
- `TestScenario`: configuração reutilizável de carga para um endpoint.
- `TestExecution`: uma execução do cenário com parâmetros históricos imutáveis.
- `MetricWindow`: medidas agregadas em um intervalo de dois segundos.
- `ModelVersion`: metadados de uma versão aprovada do modelo local.
- `RiskPrediction`: risco produzido para uma janela por determinada versão do modelo.
- `ControlDecision`: ação fixa, por regras ou assistida por IA em uma janela.
- `ExecutionReport`: resultado consolidado de uma execução concluída.

### 4.2 Conversão para o modelo relacional

O esquema inicial do PostgreSQL usará chaves primárias UUID, horários com fuso, valores textuais limitados para estados e papéis, chaves estrangeiras explícitas, unicidade para e-mail e versão do modelo e índices nas principais consultas históricas. Percentuais e probabilidades terão restrições entre zero e um. Duração, concorrência e timeout deverão ser positivos.

A migration será a fonte executável de verdade. Um arquivo `database/schema.sql` equivalente será fornecido para avaliação e geração dos diagramas, mas a evolução do banco ocorrerá por Alembic.

### 4.3 Regras de integridade

- um endpoint não pode existir sem projeto;
- um cenário deve referenciar um endpoint do mesmo projeto;
- uma execução armazena uma cópia dos limites selecionados, de forma que edições futuras do cenário não alterem o histórico;
- uma previsão referencia exatamente uma janela e uma versão do modelo;
- uma decisão referencia uma janela e pode referenciar uma previsão;
- o banco impede números de sequência repetidos dentro da mesma execução;
- a exclusão de projeto é restringida quando existem execuções históricas;
- caminhos de artefatos de modelo são somente metadados e devem apontar para armazenamento local aprovado.

## 5 Modelo de classes

O diagrama separará entidades do domínio dos módulos coordenadores. As principais classes serão `User`, `Project`, `Endpoint`, `TestScenario`, `TestExecution`, `MetricWindow`, `ModelVersion`, `RiskPrediction`, `ControlDecision`, `ExecutionReport`, `ExecutionCoordinator`, `MetricsAggregator`, `FeatureBuilder`, `RiskPredictor`, `SklearnRiskPredictor`, `ConcurrencyController`, `FixedController`, `RulesController`, `AdaptiveLoadController` e os adaptadores de persistência.

Os relacionamentos serão equivalentes ao modelo relacional. Haverá interfaces para previsão, escolha do controlador, motor de execução, relógio e persistência. Detalhes de PostgreSQL e scikit-learn não serão expostos às classes coordenadoras.

## 6 Projeto do protótipo

O protótipo representará o produto planejado, sem ser tratado como implementação de produção. Será construído para desktop, com adaptação responsiva prevista, navegação azul-escura, contraste acessível, estados identificados também por texto e padrões consistentes para tabelas e cartões de métricas.

O arquivo Figma conterá telas ligadas para:

1. login;
2. painel geral;
3. projetos e endpoints autorizados;
4. formulário de projeto e endpoint;
5. novo cenário de teste;
6. acompanhamento da execução;
7. confirmação da interrupção de emergência;
8. histórico de execuções;
9. relatório comparativo;
10. versões locais do modelo e métricas de avaliação;
11. usuários e papéis.

O fluxo principal será Login -> Painel -> Projeto -> Novo teste -> Monitoramento -> Relatório. A tela do modelo servirá à revisão da equipe técnica e não será um chatbot nem uma função superficial de IA. O monitoramento exibirá risco previsto, estratégia ativa, concorrência, última decisão, throughput, latência p95, erros e versão do modelo.

Imagens exportadas do Figma serão inseridas no documento com legendas. O documento também trará um link para o arquivo original, permitindo ampliar e navegar pelo protótipo.

## 7 Estrutura do repositório

```text
backend/
  app/
    api/
    core/
    db/
    modules/{auth,projects,load_tests,metrics,intelligence,control,reports}/
  migrations/
  tests/
frontend/
  README.md
database/
  schema.sql
  seeds/
docs/
  architecture/
  diagrams/
  prototypes/
  superpowers/specs/
docker-compose.yml
.env.example
README.md
```

Na Sprint 02, a pasta `frontend` conterá apenas notas de passagem do protótipo para implementação. Não será criada uma interface parcial. As fontes dos diagramas e as imagens exportadas serão versionadas para permitir revisões posteriores.

## 8 Estratégia para o documento da Sprint 02

O DOCX fornecido da Sprint 01 será usado como base e seu conteúdo existente permanecerá inalterado. Uma nova seção principal, `Parte II Sprint 02 Estrutura Técnica`, será acrescentada depois da seção do GitHub. Ela conterá:

- objetivo e declaração de continuidade da Sprint 02;
- arquitetura e explicação;
- diagrama de classes e explicação;
- MER conceitual e descrição das entidades;
- modelo relacional com chaves, restrições e índices;
- fluxo do protótipo e telas principais exportadas;
- evidência de criação do banco e comandos reproduzíveis;
- árvore do repositório e link;
- lista de verificação da entrega.

As figuras terão legendas numeradas, dimensões legíveis e explicações breves. Diagramas largos poderão usar páginas em orientação paisagem, sem alterar as páginas originais da Sprint 01.

## 9 Verificação

A verificação incluirá:

- análise do SQL e aplicação da migration no PostgreSQL;
- conferência de que tabelas e chaves do modelo relacional existem na migration;
- conferência dos diretórios e arquivos obrigatórios;
- abertura dos links e quadros exportados do Figma;
- renderização do DOCX final e inspeção de todas as páginas;
- auditoria de títulos, cabeçalhos de tabelas, textos alternativos e hiperlinks;
- comparação textual para confirmar que todos os parágrafos e tabelas da Sprint 01 permanecem presentes e inalterados.

## 10 Sequência de entrega

1. Alinhar o README ao escopo aprovado na Sprint 01.
2. Criar a fundação do repositório e os artefatos do banco.
3. Gerar arquitetura, diagrama de classes, MER e modelo relacional a partir de fontes versionadas.
4. Criar e vincular o protótipo Figma.
5. Acrescentar a Sprint 02 e as figuras ao DOCX fornecido.
6. Validar banco, repositório, diagramas e documento.
7. Registrar e enviar as entregas concluídas ao GitHub.
