# LoadForge

Plataforma web para planejamento, execução e análise de testes de carga controlados, com previsão local de degradação por inteligência artificial e otimização adaptativa da concorrência.

Projeto Integrador de Fábrica de Software e Tópicos Avançados da UNINASSAU, turma 2026.2.

## Problema

Equipes de desenvolvimento nem sempre conseguem medir como uma aplicação se comporta quando o volume de acessos aumenta. Um gerador de carga mal dimensionado também pode saturar a própria máquina de teste e distorcer os resultados. Controladores baseados apenas em limites fixos reagem somente depois que a degradação já começou.

O LoadForge executará cenários autorizados de carga, coletará métricas em janelas temporais, estimará o risco de degradação nos segundos seguintes e ajustará a concorrência antes que latência, erros ou perda de throughput ultrapassem os limites configurados.

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

1. **DegradationRiskModel:** recebe as métricas agregadas em janelas de dois segundos e estima a probabilidade de degradação nos dez segundos seguintes. O pipeline de preparação, rotulagem, treinamento, validação e versionamento será desenvolvido pela equipe com Python e scikit-learn.
2. **AdaptiveLoadController:** combina o risco previsto com as métricas atuais para aumentar, manter ou reduzir a concorrência. Se o modelo estiver indisponível ou receber dados inválidos, o controlador continua operando por regras.

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
| Frontend | React, Vite e TypeScript | Login, usuários, projetos e endpoints |
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

O volume nomeado `loadforge_pgdata` preserva os dados entre reinicializações. O serviço opcional `migrate` também permite aplicar as migrations isoladamente com `docker compose --profile tools run --rm migrate`. A porta do PostgreSQL fica limitada ao próprio computador (`127.0.0.1`).

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

### Testes

No diretório do backend, instale as dependências de desenvolvimento e execute:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

O teste com PostgreSQL requer um banco descartável cujo nome termine em `_test`, as migrations aplicadas e `LOADFORGE_TEST_DATABASE_URL` apontando para ele.

### Configuração sensível

O repositório mantém somente exemplos vazios de configuração. Senhas, tokens, chaves privadas e arquivos `.env` devem permanecer apenas no ambiente local ou em um gerenciador de segredos. Ao executar o backend fora do Compose, defina `DATABASE_URL` ou todos os componentes `POSTGRES_*`; não existe credencial padrão no código nem na configuração do Alembic.

Se o volume `loadforge_pgdata` já tiver sido inicializado com outra senha, alterar apenas o `.env` não modifica a credencial armazenada pelo PostgreSQL. Nesse caso, a senha do usuário deve ser rotacionada no banco existente ou, quando os dados forem descartáveis, o ambiente local pode ser recriado conscientemente.

## Segurança e uso responsável

O LoadForge deve executar testes somente contra aplicações próprias ou expressamente autorizadas. Cada cenário terá limites configuráveis de concorrência, duração e timeout, declaração de autorização e interrupção imediata.

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
