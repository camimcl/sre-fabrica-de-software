# Referência completa das APIs

Contrato: 1.0.0-rc.1. Gerado de [openapi.json](openapi.json).

Schemas completos, exemplos, tipos e limites estão no OpenAPI e em `/docs` ou `/redoc`.
UUIDs de exemplos são fictícios. Use IDs retornados pelos cadastros do seu ambiente.
Total de operações: **50**.

## GET `/audit/logs`

Consultar auditoria global

Somente QA. Histórico global do ambiente, independente do projeto selecionado. Filtros por ator, ação, entidade e período; paginação limitada. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `actor_id` | query | Não | `{"anyOf": [{"format": "uuid", "type": "string"}, {"type": "null"}], "title": "Actor Id"}` |
| `action` | query | Não | `{"anyOf": [{"$ref": "#/components/schemas/AuditAction"}, {"type": "null"}], "title": "Action"}` |
| `entity_type` | query | Não | `{"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Entity Type"}` |
| `date_from` | query | Não | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "title": "Date From"}` |
| `date_to` | query | Não | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "title": "Date To"}` |
| `page` | query | Não | `{"default": 1, "minimum": 1, "title": "Page", "type": "integer"}` |
| `page_size` | query | Não | `{"default": 20, "maximum": 100, "minimum": 1, "title": "Page Size", "type": "integer"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 422 | Validation Error application/json |

## POST `/auth/login`

Autenticar e emitir token

Envia e-mail e senha. Retorna access_token e expires_in; use Authorization: Bearer <token> nas demais chamadas. O perfil é consultado no banco em cada requisição. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Pública.

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/LoginRequest"}}}

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 422 | Validation Error application/json |

## GET `/auth/me`

Consultar perfil da sessão

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |

## POST `/auth/register`

Cadastrar conta Visualizador

Cadastro público cria somente VIEWER. Perfil extra é rejeitado; senha exige ao menos 12 caracteres. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Pública.

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/RegisterRequest"}}}

| Resposta | Significado |
|---|---|
| 201 | Successful Response application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/health/live`

Verificar disponibilidade do processo

Consulta pública de saúde do serviço. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Pública.

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |

## GET `/health/ready`

Verificar conexão com o banco

Consulta pública de saúde do serviço. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Pública.

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 503 | Banco indisponível. application/json |

## GET `/intelligence/models`

Listar versões de modelos locais

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |

## POST `/intelligence/models/train`

Treinar versão candidata com dados persistidos

Somente QA. Exige amostras temporais suficientes e duas classes. Calibração/limiar usam validação; o teste é reservado. Retorna 409 se os dados forem insuficientes. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Resposta | Significado |
|---|---|
| 201 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |

## POST `/intelligence/models/{model_id}/approve`

Aprovar modelo elegível

Somente QA. Confere artefato, hash, esquema e recall mínimo de 0,80. Uma única versão aprovada; a anterior é retirada. Não garante ganho de desempenho. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `model_id` | path | Sim | `{"format": "uuid", "title": "Model Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects`

Pesquisar projetos

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `search` | query | Não | `{"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Search"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 422 | Validation Error application/json |

## POST `/projects`

Criar projeto próprio

QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/ProjectWrite"}}}

| Resposta | Significado |
|---|---|
| 201 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## DELETE `/projects/{project_id}`

Excluir projeto sem dependências

QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 204 | Successful Response  |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}`

Consultar projeto

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## PUT `/projects/{project_id}`

Atualizar projeto próprio

QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/ProjectWrite"}}}

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/dashboard`

Consultar indicadores reais do projeto

Autenticado. Período filtra execuções e indicadores de execuções concluídas. Cenários/endpoints/comparações são totais do projeto. Série diária em UTC; P95 médio é média dos P95 das janelas, não percentil global. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `date_from` | query | Não | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "title": "Date From"}` |
| `date_to` | query | Não | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "title": "Date To"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/endpoints`

Listar endpoints do projeto

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## POST `/projects/{project_id}/endpoints`

Cadastrar endpoint e autorização

QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/EndpointWrite"}}}

| Resposta | Significado |
|---|---|
| 201 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## DELETE `/projects/{project_id}/endpoints/{endpoint_id}`

Excluir endpoint sem cenários

QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `endpoint_id` | path | Sim | `{"format": "uuid", "title": "Endpoint Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 204 | Successful Response  |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/endpoints/{endpoint_id}`

Consultar endpoint

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `endpoint_id` | path | Sim | `{"format": "uuid", "title": "Endpoint Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## PUT `/projects/{project_id}/endpoints/{endpoint_id}`

Atualizar endpoint e autorização

QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `endpoint_id` | path | Sim | `{"format": "uuid", "title": "Endpoint Id", "type": "string"}` |

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/EndpointWrite"}}}

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/executions`

Pesquisar execuções com filtros e paginação

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `status` | query | Não | `{"anyOf": [{"$ref": "#/components/schemas/ExecutionStatus"}, {"type": "null"}], "title": "Status"}` |
| `strategy` | query | Não | `{"anyOf": [{"$ref": "#/components/schemas/ControlStrategy"}, {"type": "null"}], "title": "Strategy"}` |
| `initiated_by` | query | Não | `{"anyOf": [{"format": "uuid", "type": "string"}, {"type": "null"}], "title": "Initiated By"}` |
| `date_from` | query | Não | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "title": "Date From"}` |
| `date_to` | query | Não | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "title": "Date To"}` |
| `search` | query | Não | `{"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Search"}` |
| `page` | query | Não | `{"default": 1, "minimum": 1, "title": "Page", "type": "integer"}` |
| `page_size` | query | Não | `{"default": 20, "maximum": 100, "minimum": 1, "title": "Page Size", "type": "integer"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/exports/executions.csv`

Exportar consulta de execuções em CSV

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação. Retorna arquivo para download com Content-Disposition; utiliza dados persistidos e exige relatório já gerado quando aplicável.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `status` | query | Não | `{"anyOf": [{"$ref": "#/components/schemas/ExecutionStatus"}, {"type": "null"}], "title": "Status"}` |
| `strategy` | query | Não | `{"anyOf": [{"$ref": "#/components/schemas/ControlStrategy"}, {"type": "null"}], "title": "Strategy"}` |
| `initiated_by` | query | Não | `{"anyOf": [{"format": "uuid", "type": "string"}, {"type": "null"}], "title": "Initiated By"}` |
| `date_from` | query | Não | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "title": "Date From"}` |
| `date_to` | query | Não | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "title": "Date To"}` |
| `search` | query | Não | `{"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Search"}` |

| Resposta | Significado |
|---|---|
| 200 | Arquivo exportado com sucesso. text/csv |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/reports/comparisons`

Listar comparações persistidas

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## POST `/projects/{project_id}/reports/comparisons`

Comparar estratégias em condições equivalentes

QA proprietário. De 9 a 90 IDs únicos, três estratégias, pelo menos três repetições por estratégia, quantidades iguais e condições equivalentes. Todas concluídas. Falha aborta a transação. Fallback não comprova ganho da IA. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/ComparisonCreateRequest"}}}

| Resposta | Significado |
|---|---|
| 201 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/reports/comparisons/{comparison_id}`

Consultar comparação

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `comparison_id` | path | Sim | `{"format": "uuid", "title": "Comparison Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/reports/comparisons/{comparison_id}.csv`

Exportar comparação em CSV

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação. Retorna arquivo para download com Content-Disposition; utiliza dados persistidos e exige relatório já gerado quando aplicável.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `comparison_id` | path | Sim | `{"format": "uuid", "title": "Comparison Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Arquivo exportado com sucesso. text/csv |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/reports/comparisons/{comparison_id}.pdf`

Exportar comparação em PDF

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação. Retorna arquivo para download com Content-Disposition; utiliza dados persistidos e exige relatório já gerado quando aplicável.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `comparison_id` | path | Sim | `{"format": "uuid", "title": "Comparison Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Arquivo exportado com sucesso. application/pdf |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/reports/executions`

Consultar histórico com relatórios

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/scenarios`

Pesquisar cenários

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `search` | query | Não | `{"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Search"}` |
| `strategy` | query | Não | `{"anyOf": [{"$ref": "#/components/schemas/ControlStrategy"}, {"type": "null"}], "title": "Strategy"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## POST `/projects/{project_id}/scenarios`

Criar cenário autorizado

QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/ScenarioWrite"}}}

| Resposta | Significado |
|---|---|
| 201 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## DELETE `/projects/{project_id}/scenarios/{scenario_id}`

Excluir cenário sem execuções

QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 204 | Successful Response  |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/scenarios/{scenario_id}`

Consultar cenário

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## PUT `/projects/{project_id}/scenarios/{scenario_id}`

Atualizar cenário preservando snapshots

QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/ScenarioWrite"}}}

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/scenarios/{scenario_id}/executions`

Listar execuções do cenário

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## POST `/projects/{project_id}/scenarios/{scenario_id}/executions`

Criar execução com confirmação explícita

QA proprietário. authorization_acknowledged deve ser booleano JSON true. Congela alvo e configurações; não inicia tráfego. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionCreateRequest"}}}

| Resposta | Significado |
|---|---|
| 201 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}`

Consultar execução

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## POST `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/cancel`

Solicitar parada emergencial

QA proprietário. Impede novas requisições; aguarda as em voo até resposta/timeout. Enquanto drena pode retornar RUNNING; consulte novamente até CANCELLED. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/ExecutionCancelRequest"}}}

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## POST `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/complete`

Concluir execução sem motor ativo

QA proprietário. Retorna 409 se houver motor ativo; use cancel para interromper o tráfego. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/control-decisions`

Consultar decisões de controle

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## POST `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/fail`

Marcar falha sem motor ativo

QA proprietário. Retorna 409 se houver motor ativo; use cancel para interromper o tráfego. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/metric-windows`

Consultar métricas coletadas por janela

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/report`

Consultar relatório individual persistido

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## POST `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/report`

Gerar relatório de execução terminal

QA proprietário. Exige execução terminal com métricas. O relatório é persistido e pode ser consultado/exportado por usuários autenticados. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 201 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/report.pdf`

Exportar relatório individual em PDF

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação. Retorna arquivo para download com Content-Disposition; utiliza dados persistidos e exige relatório já gerado quando aplicável.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Arquivo exportado com sucesso. application/pdf |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## GET `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/risk-predictions`

Consultar previsões por janela

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 422 | Validation Error application/json |

## POST `/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/start`

Iniciar tráfego autorizado

QA proprietário. Revalida autorização e snapshot. Transição PENDING → RUNNING; execução assíncrona. Consulte o estado e as métricas. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `project_id` | path | Sim | `{"format": "uuid", "title": "Project Id", "type": "string"}` |
| `scenario_id` | path | Sim | `{"format": "uuid", "title": "Scenario Id", "type": "string"}` |
| `execution_id` | path | Sim | `{"format": "uuid", "title": "Execution Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## GET `/users`

Pesquisar usuários

Consulta autenticada no ambiente compartilhado. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `search` | query | Não | `{"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Search"}` |
| `role` | query | Não | `{"anyOf": [{"$ref": "#/components/schemas/UserRole"}, {"type": "null"}], "title": "Role"}` |

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 422 | Validation Error application/json |

## POST `/users`

Criar conta como QA

Somente QA. Alteração persistida e validada pela API. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/UserCreateRequest"}}}

| Resposta | Significado |
|---|---|
| 201 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## DELETE `/users/{user_id}`

Excluir conta respeitando dependências

Própria conta ou QA. O último QA e contas com dependências não podem ser excluídos. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `user_id` | path | Sim | `{"format": "uuid", "title": "User Id", "type": "string"}` |

| Resposta | Significado |
|---|---|
| 204 | Successful Response  |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

## PUT `/users/{user_id}`

Atualizar conta e perfil

Própria conta ou QA. Somente QA muda perfis. Não é permitido remover o último QA nem despromover o proprietário de projetos. Os parâmetros, limites e schemas abaixo integram o contrato desta operação.

Autenticação: Bearer obrigatório.

| Parâmetro | Local | Obrigatório | Tipo / contrato |
|---|---|---|---|
| `user_id` | path | Sim | `{"format": "uuid", "title": "User Id", "type": "string"}` |

Corpo: {"application/json": {"schema": {"$ref": "#/components/schemas/UserUpdateRequest"}}}

| Resposta | Significado |
|---|---|
| 200 | Successful Response application/json |
| 401 | Credenciais ausentes, inválidas ou expiradas. application/json |
| 403 | Perfil ou propriedade sem permissão para a operação. application/json |
| 404 | Recurso inexistente ou fora do contexto informado. application/json |
| 409 | Conflito de estado, dependência, duplicidade ou regra de negócio. application/json |
| 422 | Validation Error application/json |

