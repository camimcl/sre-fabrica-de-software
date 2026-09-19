# Relatório Técnico da Sprint 03

## Objetivo

A Sprint 03 transforma a estrutura técnica da Sprint 02 em uma aplicação local executável. O fluxo implementado conecta interface, API e PostgreSQL e permite demonstrar autenticação, controle de acesso e persistência real do cadastro principal.

## Arquitetura executável

O ambiente local contém três serviços:

1. **Frontend:** aplicação React compilada e entregue pelo Nginx.
2. **API:** aplicação FastAPI que valida dados, autentica usuários, aplica permissões e executa o CRUD.
3. **Banco:** PostgreSQL com esquema criado pelas migrations Alembic da Sprint 02.

O frontend acessa somente a API. A API usa SQLAlchemy para consultar e alterar o banco. A porta do PostgreSQL e as portas web são vinculadas a `127.0.0.1`, mantendo o ambiente restrito ao computador local.

## Autenticação e perfis

Senhas são armazenadas como derivação PBKDF2-HMAC-SHA256 com salt aleatório e 600 mil iterações. Após o login, a API emite um token assinado com validade de oito horas. A chave de assinatura é fornecida por variável de ambiente e não é incluída no repositório.

Os perfis iniciais são:

| Perfil | Permissões implementadas |
|---|---|
| QA | Consultar dados; criar usuários; criar projetos; alterar e excluir projetos próprios; manter endpoints dos projetos próprios. |
| Visualizador | Consultar projetos e endpoints; consultar os dados da própria sessão. |

O cadastro público cria sempre um Visualizador. A primeira conta QA é criada por um comando local e as contas seguintes podem ser cadastradas por um QA autenticado.

## CRUD principal

Projetos são a entidade principal desta etapa e endpoints formam o cadastro dependente. O CRUD implementado oferece criação, consulta, atualização e exclusão reais. As operações passam pela API e são confirmadas no PostgreSQL. A exclusão respeita as referências do modelo: um projeto com endpoints ou cenários dependentes não é removido antes que essas dependências sejam tratadas.

Endpoints aceitam somente métodos HTTP previstos no esquema. A URL é validada e não pode conter credenciais embutidas. Quando a autorização do alvo é marcada como confirmada, uma evidência textual se torna obrigatória.

## Evidências dos requisitos

| Requisito | Evidência executável |
|---|---|
| Banco conectado | `GET /health/ready` executa `SELECT 1`; migration aplicada em PostgreSQL; teste de integração confirma leitura e escrita. |
| Login funcional | `POST /auth/login`, senha derivada e token assinado; `GET /auth/me` recupera o usuário persistido. |
| Cadastro de usuários | `POST /auth/register` cria Visualizador; `POST /users` permite ao QA criar QA ou Visualizador. |
| Controle de perfis | Dependências de autorização bloqueiam mutações para Visualizador e exigem propriedade do projeto. |
| CRUD principal | Rotas `/projects` e `/projects/{id}/endpoints` implementam cadastrar, consultar, atualizar e excluir. |
| Deploy local | `docker compose up --build` inicia PostgreSQL, aplica migrations, inicia API e publica o frontend local. |

## Validação

A suíte automatizada cobre configuração, segurança, modelos, contratos, autenticação, perfis e CRUD. Um teste separado, protegido por uma URL de banco com sufixo `_test`, aplica o fluxo completo em PostgreSQL. O frontend é validado pelo build de produção e pelo fluxo visual de login e cadastro conectado à API.
