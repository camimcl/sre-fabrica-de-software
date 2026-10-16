# LoadForge

Plataforma web para planejamento, execução e análise de testes de carga controlados, com previsão local de degradação por inteligência artificial e otimização adaptativa da concorrência.

Projeto Integrador de Fábrica de Software e Tópicos Avançados da UNINASSAU, turma 2026.2.

## Problema

Equipes de desenvolvimento nem sempre conseguem medir como uma aplicação se comporta quando o volume de acessos aumenta. Um gerador de carga mal dimensionado também pode saturar a própria máquina de teste e distorcer os resultados. Controladores baseados apenas em limites fixos reagem somente depois que a degradação já começou.

O LoadForge executa cenários autorizados de carga, coleta métricas em janelas temporais, estima o risco de degradação nas cinco janelas seguintes (dez segundos nominais) e usa esse sinal para ajustar a concorrência. A antecedência e o ganho de desempenho são medidos experimentalmente, não garantidos pelo algoritmo.

## Escopo do MVP

O MVP contempla:

- autenticação com perfis de QA e Visualizador;
- cadastro de projetos e endpoints autorizados;
- configuração de duração, concorrência, ramp-up e timeout;
- motor assíncrono de requisições HTTP em Python;
- coleta de throughput, latências, erros, timeouts, CPU e memória;
- formação de conjunto de dados próprio;
- treinamento e validação local de modelos preditivos;
- comparação entre regressão logística e Random Forest;
- inferência local de risco de degradação;
- controlador adaptativo com fallback por regras;
- comparação entre carga fixa, controle por regras e controle assistido por IA;
- persistência das configurações, métricas, previsões, decisões e resultados;
- relatórios e histórico das execuções.

Não fazem parte do MVP: chatbot, IA generativa, consumo de API externa de IA, execução distribuída em cluster, CUDA, aceleração por GPU, Celery, Redis, aplicativo móvel, cobrança, arquitetura multi-tenant ou plugins.

## Inteligência artificial e otimização

O diferencial computacional é formado por dois módulos:

1. **DegradationRiskModel:** recebe métricas agregadas em janelas de dois segundos nominais e estima a probabilidade de degradação nas cinco janelas seguintes. O tempo observado inclui as requisições em voo e pode exceder o nominal. O pipeline local prepara características e rótulos, divide os dados cronologicamente, compara regressão logística e Random Forest e versiona o candidato vencedor com métricas e hashes auditáveis.
2. **AdaptiveLoadController:** combina o risco previsto com as métricas atuais para aumentar, manter ou reduzir a concorrência. Se não houver modelo aprovado ou a inferência falhar, o controlador continua por regras e persiste o motivo do fallback.

O contrato preditivo é de **cinco janelas futuras**, não dez segundos exatos de relógio. As versões novas registram `prediction_horizon` com tipo, quantidade de janelas, duração nominal e extremos observados do intervalo. As fronteiras temporais usam o fim da observação de cada janela; assim, requisições lentas não são descritas nos metadados como um horizonte fixo.

A avaliação utilizará precisão, recall, F1, falsos positivos, antecedência da previsão, latência de inferência, throughput, latência p95, taxa de erro, uso de CPU e estabilidade do controle.

## Arquitetura prevista para o MVP

O projeto adotará um monólito modular em um único repositório:

```text
Navegador
   |
   | HTTP REST
   v
Frontend React
   |
   | JSON
   v
API FastAPI
   |-- usuários, projetos e endpoints
   |-- cenários e execuções
   |-- métricas e relatórios
   |-- pipeline de IA
   |-- controlador adaptativo
   |
   +----> PostgreSQL
   |
   +----> modelo local versionado
   |
   +----> aplicação autorizada sob teste
```

Essa arquitetura mantém as responsabilidades separadas por módulos, mas evita a complexidade operacional de microserviços, filas distribuídas e aceleração especializada antes que o fluxo principal esteja validado.

Os diagramas técnicos foram organizados com um caminho principal da esquerda para a direita e desdobramentos abaixo da entidade de origem. Para evitar linhas sobrepostas, referências secundárias aparecem como atributos UUID ou chaves estrangeiras dentro das tabelas. O [guia de leitura](docs/diagrams/README.md) reúne as convenções, as fontes editáveis e as exportações oficiais.

## Tecnologias

| Camada | Tecnologia | Responsabilidade |
|---|---|---|
| Frontend | React, Vite e TypeScript | Cadastro, cenários, execução, monitor adaptativo e modelos |
| Backend | Python 3.11 e FastAPI | Regras da aplicação e interface HTTP |
| Persistência | PostgreSQL 16 | Usuários, projetos, cenários, execuções, métricas, modelos e decisões |
| Mapeamento e migrations | SQLAlchemy 2 e Alembic | Modelo relacional e evolução do esquema |
| Motor de carga | Python asyncio e httpx | Requisições concorrentes com limites e cancelamento |
| IA local | scikit-learn e joblib | Treinamento, avaliação, versionamento e inferência |
| Ambiente | Docker Compose | Frontend, API, migrations e banco local |
| Testes | pytest | Validação dos módulos e do fluxo integrado |

## Estrutura do repositório

```text
backend/
  app/
    api/
    core/
    db/
    modules/
      auth/
      projects/
      load_tests/
      metrics/
      intelligence/
      control/
  migrations/
  tests/
frontend/
  src/
    pages/
    components/
    navigation/
database/
  schema.sql
  seeds/
docs/
  architecture/
  diagrams/
  prototypes/
  relatorio-sprint-02.md
docker-compose.yml
.env.example
```

## Sprint 02

A arquitetura, os modelos, o esquema inicial do PostgreSQL e o protótipo das telas estão consolidados no [Relatório Técnico da Sprint 02](docs/relatorio-sprint-02.md). As fontes editáveis e as imagens dos diagramas ficam em [`docs/diagrams`](docs/diagrams/README.md).

O protótipo editável está no [Figma — LoadForge Sprint 02](https://www.figma.com/design/isw6HZdCiomQvSekNScl9J), com descrição e capturas em `docs/prototypes/`. Ele funciona como referência inicial para navegação e organização das informações; a interface poderá mudar durante a implementação e os testes de usabilidade.

## Sprint 03

A aplicação possui um primeiro fluxo executável com banco conectado, cadastro, login, perfis QA e Visualizador e CRUD persistido de usuários, projetos e endpoints. A interface React consome a API FastAPI, e as regras de acesso são aplicadas no backend. Cada usuário pode atualizar ou excluir a própria conta; o QA também gerencia outras contas. A aplicação preserva ao menos um QA e impede a exclusão de usuários com projetos ou execuções vinculados. Consulte o [Relatório Técnico da Sprint 03](docs/relatorio-sprint-03.md) para a arquitetura executável e as evidências de cada requisito.

## Sprint 04

O módulo de testes de carga (`load_tests`) foi implementado com CRUD de cenários e ciclo de vida de execuções persistido, validações de negócio, mensagens de erro claras e a invariante de segurança de alvo autorizado. Sobre essa base, o motor de geração de carga real (`asyncio` + `httpx`) dispara requisições concorrentes contra o endpoint autorizado, coleta métricas por janela temporal (persistidas em `metric_windows`) e oferece parada de emergência efetiva. O motor roda em tarefa assíncrona em background e não bloqueia a API; a persistência das janelas usa a sessão síncrona fora do event loop.

## Sprint 05

O segundo módulo funcional integra `intelligence` e `control` ao motor de carga. A aplicação forma um conjunto de dados próprio com as janelas persistidas, rotula a ocorrência de degradação nas cinco janelas futuras, nominalmente dez segundos e com duração observada variável, compara dois algoritmos locais e armazena a versão candidata com precisão, recall, F1, acurácia e hashes do conjunto e do artefato. Um QA pode aprovar uma versão; as execuções `AI_HYBRID` passam a persistir uma previsão e uma decisão por janela, enquanto a ausência ou falha do modelo ativa o fallback por regras sem interromper o teste.

O painel React agora permite criar cenários, iniciar e interromper execuções, acompanhar métricas, riscos e decisões e administrar versões do modelo. A explicação técnica, as regras atualizadas, os testes e o registro de bugs estão no [Relatório Técnico da Sprint 05](docs/relatorio-sprint-05.md).

## Como executar localmente com Docker

1. Copie `.env.example` para `.env`.
2. Defina valores locais fortes e exclusivos para `POSTGRES_PASSWORD` e `LOADFORGE_TOKEN_SECRET`. A chave de token deve ter ao menos 32 caracteres. Mantenha o `.env` fora do controle de versão.
3. Inicie o ambiente:

   ```bash
   docker compose up --build -d
   ```

   A API aguarda o banco, aplica as migrations e inicia. O frontend aguarda a API ficar saudável.

4. Crie a primeira conta QA. A senha é digitada de forma interativa e não aparece no histórico do terminal:

   ```bash
   docker compose exec api python -m app.cli create-qa --name "Nome do QA" --email "qa@exemplo.com"
   ```

5. Abra `http://127.0.0.1:5173` e entre com a conta criada. A documentação interativa da API fica em `http://127.0.0.1:8000/docs`.
6. Confira o estado dos serviços:

   ```bash
   docker compose ps
   ```

7. Para encerrar sem apagar os dados:

   ```bash
   docker compose down
   ```

Os volumes nomeados `loadforge_pgdata` e `loadforge_model_artifacts` preservam, respectivamente, os dados e os modelos aprováveis entre reinicializações. O serviço opcional `migrate` também permite aplicar as migrations isoladamente com `docker compose --profile tools run --rm migrate`. A porta do PostgreSQL fica limitada ao próprio computador (`127.0.0.1`).

### Rotas principais

| Método e rota | Acesso | Finalidade |
|---|---|---|
| `GET /health/ready` | Público | Confirma a conexão real com o banco. |
| `POST /auth/register` | Público | Cria uma conta Visualizador. |
| `POST /auth/login` | Público | Autentica por e-mail e senha. |
| `GET /auth/me` | Autenticado | Consulta o perfil da sessão. |
| `GET /users` e `POST /users` | QA | Lista e cria usuários. |
| `PUT /users/{id}` e `DELETE /users/{id}` | Próprio usuário/QA | Atualiza ou exclui a própria conta; QA também gerencia outras contas. |
| `/projects` | Autenticado/QA | Consulta para ambos; mutações para QA. |
| `/projects/{id}/endpoints` | Autenticado/QA | Consulta para ambos; mutações pelo QA proprietário. |
| `/projects/{id}/scenarios` | Autenticado/QA | Consulta para ambos; mutações pelo QA proprietário. |
| `/projects/{id}/scenarios/{id}/executions` | Autenticado/QA | Consulta para ambos; criação e transições de estado pelo QA proprietário. |
| `.../executions/{id}/start` e `/cancel` | QA proprietário | Inicia a geração de carga real (assíncrona) e a parada de emergência efetiva. |
| `.../executions/{id}/metric-windows` | Autenticado | Consulta as janelas de métricas coletadas durante a execução (polling). |
| `.../executions/{id}/risk-predictions` | Autenticado | Consulta as previsões persistidas por janela. |
| `.../executions/{id}/control-decisions` | Autenticado | Consulta as ações e justificativas do controlador. |
| `GET /intelligence/models` | Autenticado | Lista versões, estados e métricas dos modelos locais. |
| `POST /intelligence/models/train` | QA | Treina e persiste uma nova versão candidata. |
| `POST /intelligence/models/{id}/approve` | QA | Valida o artefato e aprova uma única versão para inferência. |

### Testes

No diretório do backend, instale as dependências de desenvolvimento e execute:

```bash
uv sync --locked --extra dev --no-install-project
uv run --no-sync pytest -q
```

Em 03/10/2026, a suíte apresentou **64 testes aprovados**, sem falhas e sem testes ignorados. Cinco casos requerem PostgreSQL, incluindo a migração de históricos compatíveis e o bloqueio preventivo de históricos fora dos limites. Esses testes exigem um banco descartável cujo nome termine em `_test`, as migrations aplicadas e `LOADFORGE_TEST_DATABASE_URL` apontando para ele. Não use um banco de produção.

O [relatório da Sprint 05](docs/relatorio-sprint-05.md) registra build Docker, fluxo real de IA, persistência após reinício e navegação. As [evidências identificadas](docs/evidences/sprint-05/README.md) incluem as capturas e os resultados, sem credenciais. A interface foi exercitada com serviços reais, incluindo uma resposta de rede deliberadamente atrasada para conferir o isolamento da seleção.

O teste de navegador `frontend/tests/navigation-race.cjs` requer Playwright, um navegador instalado e um laboratório já populado. Configure `LOADFORGE_E2E_URL`, `LOADFORGE_E2E_EMAIL`, `LOADFORGE_E2E_PASSWORD` e `LOADFORGE_E2E_FIXTURE` no ambiente, nunca no código. O fixture segue a estrutura de `docs/evidences/sprint-05/fluxo-api.json` e seus IDs devem existir no laboratório utilizado; as credenciais não fazem parte do fixture. Execute `node frontend/tests/navigation-race.cjs`. O navegador padrão é Edge; `LOADFORGE_BROWSER` permite outro canal instalado.

### Integração contínua

O workflow [LoadForge CI](.github/workflows/ci.yml) executa, em PRs para `main` e pushes nessa branch, três verificações: suíte Python com PostgreSQL 16 e migrations, compilação TypeScript/Vite e construção das imagens Docker. O backend exige testes sem falhas nem skips e disponibiliza o relatório XML. O ambiente é descartável e não utiliza o banco ou as credenciais locais da equipe.

Não há deploy, publicação de imagens ou merge automático. Os testes de navegação continuam locais até que exista uma preparação independente de dados de teste. Consulte o [guia de integração contínua](docs/integracao-continua.md) para acompanhar falhas, conhecer os limites e configurar separadamente os checks obrigatórios da `main`.

### Atualização de bases antigas

A migration `20261001_0003` faz uma pré-verificação transacional dos limites de cenários e execuções. Se encontrar históricos incompatíveis, aborta com a mensagem `Sprint 05 preflight` e as contagens, antes de adicionar colunas ou atualizar registros. A equipe deve examinar esses dados e definir uma estratégia de preservação antes de repetir a migração. Não há exclusão nem redução automática de valores históricos. Bases compatíveis mantêm os registros e recebem o snapshot de ramp-up.

`backend/uv.lock` fixa as dependências diretas e transitivas. A imagem da API instala a exportação `backend/requirements.lock` com verificação obrigatória de hashes, sem resolver versões novas a cada build. A execução local usa o código a partir do diretório `backend`, sem precisar instalar o próprio projeto como pacote editável. Para atualizar dependências intencionalmente, execute `uv lock --upgrade`, regenere com `uv export --frozen --no-emit-project --no-dev --no-header --output-file requirements.lock` e execute novamente os testes antes de registrar os dois arquivos. O lockfile não substitui auditoria de vulnerabilidades nem fixa a imagem-base do sistema operacional.

### Configuração sensível

O repositório mantém somente exemplos vazios de configuração. Senhas, tokens, chaves privadas e arquivos `.env` devem permanecer apenas no ambiente local ou em um gerenciador de segredos. Ao executar o backend fora do Compose, defina `DATABASE_URL` ou todos os componentes `POSTGRES_*`; não existe credencial padrão no código nem na configuração do Alembic. Artefatos `joblib` não são versionados: ficam no diretório definido por `LOADFORGE_MODEL_DIR`, e a aplicação confere caminho, versão, esquema de atributos e SHA-256 antes de carregá-los.

Se o volume `loadforge_pgdata` já tiver sido inicializado com outra senha, alterar apenas o `.env` não modifica a credencial armazenada pelo PostgreSQL. Nesse caso, a senha do usuário deve ser rotacionada no banco existente ou, quando os dados forem descartáveis, o ambiente local pode ser recriado conscientemente.

## Segurança e uso responsável

O LoadForge deve executar testes somente contra aplicações próprias ou expressamente autorizadas. Cada cenário possui limites máximos de concorrência, duração e timeout, declaração de autorização e parada emergencial. A parada impede novas requisições; as já iniciadas são encerradas conforme a resposta ou o timeout. Em implantação compartilhada, a rede de saída da API também deve ser restringida por política de infraestrutura para impedir acesso a destinos internos não autorizados.

## Equipe

**Turma:** CC8NB

| Integrante | GitHub | Papel |
|---|---|---|
| Camile Marcele Pereira de Araújo | [@camimcl](https://github.com/camimcl) | Product Owner e Analista de QA |
| Ricardo Cezar Ottoni Assis de Almeida | [@RicardoAlmeida06](https://github.com/RicardoAlmeida06) | Dados, infraestrutura e documentação |
| Aline Bianca Arantes da Silva | [@aline-exe](https://github.com/aline-exe) | Desenvolvimento backend em Python |
| Emerson Wallace Barcelos de Araújo | [@itswall](https://github.com/itswall) | Scrum Master e desenvolvimento backend |
| Cayo Vitor Fagundes | [@cayo-vitor](https://github.com/cayo-vitor) | Desenvolvimento frontend e UI UX |

**Orientação:** Prof. Antenor Parnaíba e Prof.ª Pryscilla Gonçalves.
