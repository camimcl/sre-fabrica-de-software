# APIs do LoadForge

O produto utiliza API REST FastAPI. Endereços padrão:

- API direta: `http://127.0.0.1:8000`.
- Swagger interativo: `http://127.0.0.1:8000/docs`.
- ReDoc: `http://127.0.0.1:8000/redoc`.
- Contrato servido: `http://127.0.0.1:8000/openapi.json`.
- O frontend encaminha `/api/*` para a API; não acrescente `/api` ao usar a porta 8000.

A [referência por operação](referencia.md) lista todas as rotas, métodos,
parâmetros, entradas e respostas. O [OpenAPI versionado](openapi.json) contém
schemas completos, limites, enumerações e exemplos de todos os corpos de entrada.

## Autenticação e permissões

Crie o primeiro QA com `docker compose exec api python -m app.cli create-qa --name
"Responsável" --email "qa@example.org"`. A senha é lida interativamente, sem
credencial padrão. O cadastro público `/auth/register` cria somente VIEWER.

`POST /auth/login` recebe `{ "email": "<email>", "password": "<senha>" }` e
responde 200 com `access_token`, `token_type: "bearer"` e `expires_in` (segundos).
Use `Authorization: Bearer <access_token>` nas requisições protegidas. No Swagger,
cole somente o token em **Authorize**, depois de efetuar login. Tokens expiram;
credenciais inválidas retornam 401. Nunca versione o token ou a resposta real de login.

O ambiente é compartilhado. Visualizadores consultam projetos e resultados e
gerenciam a própria conta. QA administra usuários e modelos; alterar recursos de
um projeto, disparar carga ou gerar relatórios exige ser seu proprietário.
Auditoria é global e exclusiva de QA. Bloqueios retornam 403.

## Exemplo de consulta em PowerShell

```powershell
$baseUrl = 'http://127.0.0.1:8000'
$credential = Get-Credential -Message 'Informe o e-mail e a senha do LoadForge'
$body = @{ email = $credential.UserName; password = $credential.GetNetworkCredential().Password } | ConvertTo-Json
$session = Invoke-RestMethod -Method Post -Uri "$baseUrl/auth/login" -ContentType 'application/json' -Body $body
$headers = @{ Authorization = "Bearer $($session.access_token)" }
Invoke-RestMethod -Uri "$baseUrl/auth/me" -Headers $headers
Invoke-RestMethod -Uri "$baseUrl/projects" -Headers $headers
```

## Fluxo integrado e exemplos de entrada

1. `POST /projects` com `{ "name": "Homologação", "description": "Alvo autorizado" }`.
   Retorna 201; guarde o `id` real do projeto.
2. `POST /projects/{project_id}/endpoints` com `name`, `base_url`, `http_method`,
   `authorization_confirmed: true` e `authorization_evidence`. Use somente alvo
   próprio ou expressamente autorizado; o exemplo do contrato não concede autorização.
3. `POST /projects/{project_id}/scenarios` usando o `endpoint_id` retornado e o
   exemplo `ScenarioWrite` do Swagger. Limites: duração 1-3600 s, concorrência
   1-500, inicial <= máxima, ramp-up 0-500, timeout 1-60000 ms, erro 0-1.
4. `POST .../scenarios/{scenario_id}/executions` com
   `{ "authorization_acknowledged": true }`. Retorna 201/PENDING e congela o
   alvo/configuração. Textos ou números não substituem o booleano JSON.
5. `POST .../executions/{execution_id}/start` inicia o motor. Consulte GET da
   execução e `metric-windows`, `risk-predictions`, `control-decisions` até estado
   terminal. O início revalida a autorização do alvo.
6. `POST .../executions/{execution_id}/cancel` com
   `{ "cancellation_reason": "Parada solicitada pelo responsável" }` interrompe
   novas requisições. O retorno pode permanecer RUNNING enquanto drena as chamadas
   em voo; consulte até CANCELLED. O timeout limita essa drenagem.
7. `POST .../executions/{execution_id}/report` gera relatório da execução terminal
   com métricas. GET na mesma rota recupera o relatório; `.pdf` baixa o arquivo.
8. `POST /projects/{project_id}/reports/comparisons` com `name` e `execution_ids`:
   IDs únicos, de 9 a 90 execuções concluídas; mínimo de três por estratégia e
   mesma quantidade para FIXED, RULES e AI_HYBRID, com condições equivalentes.
   Os IDs fictícios do exemplo devem ser substituídos por execuções reais.
9. Consulte `dashboard`, `executions` e `audit/logs` conforme o perfil. As
   comparações disponibilizam `.csv` e `.pdf`; a consulta exporta
   `/projects/{project_id}/exports/executions.csv` com os mesmos filtros.

## Consultas e respostas

- Datas ISO 8601, preferencialmente com fuso (`2026-11-13T00:00:00-03:00`). Sem fuso,
  a API normaliza como UTC. Intervalo invertido retorna 422. O frontend converte
  dias do calendário local; a série diária é agrupada em UTC.
- Pesquisa por nome de cenário, `status`, `strategy`, `initiated_by` e período
  estão disponíveis na consulta de execuções; `page >= 1`, `page_size` limitado
  conforme OpenAPI. A exportação contém todos os registros filtrados, sem paginação.
- 200: consulta/operação; 201: recurso criado; 204: exclusão sem corpo.
- 401: autenticação; 403: permissão; 404: recurso/contexto; 409: regra, duplicidade,
  dependência ou transição; 422: validação; 503: banco indisponível no readiness.
- Erro de negócio: `{ "detail": "<explicação>" }`. Validação: `detail` é uma lista
  com `loc`, `msg` e `type`. Clientes devem tratar ambos os formatos.
- CSV: `text/csv`; PDF: `application/pdf`; cabeçalho `Content-Disposition:
  attachment; filename=...`. PDF exige relatório existente. Os arquivos não são JSON.
- Throughput usa o tempo observado. P95 médio é média dos P95 das janelas, não o
  percentil global. Resultados híbridos em fallback não comprovam ganho da IA.

## Atualizar a documentação

No backend: `python -m app.cli export-openapi --output ../docs/api/openapi.json`.
Na raiz: `python scripts/export_api_reference.py`. O teste de contrato detecta
divergência entre a aplicação e o arquivo versionado; `--check` verifica o índice.
Nenhum comando de exportação precisa de acesso ao banco.
