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

## Tecnologias previstas

| Camada | Tecnologia | Responsabilidade |
|---|---|---|
| Frontend | React, Vite e TypeScript | Protótipos navegáveis e futura interface web |
| Backend | Python 3.11 e FastAPI | Regras da aplicação e interface HTTP |
| Persistência | PostgreSQL 16 | Usuários, projetos, cenários, execuções, métricas, modelos e decisões |
| Mapeamento e migrations | SQLAlchemy 2 e Alembic | Modelo relacional e evolução do esquema |
| Motor de carga | Python asyncio e httpx | Requisições concorrentes com limites e cancelamento |
| IA local | scikit-learn e joblib | Treinamento, avaliação, versionamento e inferência |
| Ambiente | Docker Compose | API, banco e ferramentas de desenvolvimento |
| Testes | pytest | Validação dos módulos e do fluxo integrado |

## Estrutura prevista do repositório

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
  superpowers/specs/
docker-compose.yml
.env.example
```

## Situação da Sprint 02

Nesta Sprint serão entregues a arquitetura, o diagrama de classes, o modelo entidade-relacionamento, o modelo relacional, os protótipos das telas principais, o esquema inicial do PostgreSQL e a estrutura organizada do projeto. Os protótipos representam o produto completo planejado, mas não equivalem a uma interface funcional nesta etapa.

A especificação técnica aprovada está em `docs/superpowers/specs/2026-09-17-sprint-02-foundation-design.md`.

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
