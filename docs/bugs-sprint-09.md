# Registro de bugs - Sprint 09

Como QA/PO, registrei os defeitos a partir de reprodução e reteste automatizados. Todos os quatro abaixo foram corrigidos. A severidade considera impacto funcional; não equivale a exploração comprovada.

## S09-B01 - Confirmação de autorização convertida implicitamente

Severidade: Alta. Estado: corrigido e retestado.

**Procedimento e resultado anterior:** POST/PUT de endpoint com authorization_confirmed="yes", "true", "1", 1 ou 0. Antes: 201/200 e conversão automática. Esperado: 422, sem alteração.

**Causa e correção:** EndpointWrite usa Field(default=False, strict=True). Booleanos reais continuam aceitos; evidência continua obrigatória quando true.

**Resultado obtido:** 14 testes aprovados; reprodução anterior: 10 falhas e 4 controles aprovados.

**Reprodutor:** `backend/tests/test_sprint09_authorization.py`. **Evidências:** `docs/evidences/sprint-09/authorization-before.txt / authorization-after.txt`.

## S09-B02 - Mensagem de erro quebrava com JSON null

Severidade: Média. Estado: corrigido e retestado.

**Procedimento e resultado anterior:** Resposta HTTP 502 com corpo JSON null em API/download. Antes: TypeError ao ler detail. Esperado: mensagem contendo operação/exportação e status.

**Causa e correção:** Leitura segura data?.detail em api.ts e download.ts. Mantém tratamento de mensagens de validação e conteúdo não JSON.

**Resultado obtido:** 11 testes de frontend aprovados; o caso null falhou antes.

**Reprodutor:** `frontend/tests/sprint09.test.mjs`. **Evidências:** `docs/evidences/sprint-09/frontend-before.txt / frontend-after.txt`.

## S09-B03 - Resposta de endpoint misturava projetos

Severidade: Alta. Estado: corrigido e retestado.

**Procedimento e resultado anterior:** Salvar endpoint em A; retardar resposta real; selecionar B e digitar rascunho; liberar A. Antes: endpoint de A aparecia em B e rascunho era limpo.

**Causa e correção:** Contador de contexto invalida atualização de lista, mensagens e limpeza de formulário após troca de projeto/sessão; cobre salvar e excluir.

**Resultado obtido:** NAV-RACE-01 passou; banco manteve endpoint em A e nenhum em B.

**Reprodutor:** `scripts/qa/context-race.mjs`. **Evidências:** `docs/evidences/sprint-09/race-before.json / race-after.json`.

## S09-B04 - Carregamento preso com intervalo inválido

Severidade: Média. Estado: corrigido e retestado.

**Procedimento e resultado anterior:** Abrir dashboard com resposta pendente; preencher De=07/11 e Até=06/11; liberar resposta. Antes: validação aparecia junto de Carregando indicadores indefinidamente.

**Causa e correção:** Limpa loading quando validRange é falso e mantém descarte da resposta antiga.

**Resultado obtido:** NAV-RACE-02 passou; sem dados antigos/carregamento e indicadores recuperados ao limpar filtros.

**Reprodutor:** `scripts/qa/dashboard-race.mjs`. **Evidências:** `docs/evidences/sprint-09/dashboard-before.json / dashboard-after.json`.

## Ocorrências do laboratório e dos testes

- O primeiro contexto SQLite não ativava chaves estrangeiras. A expectativa 409 recebia 204. A preparação do teste foi corrigida com PRAGMA foreign_keys=ON e os 28 casos passaram; a mesma proteção foi comprovada no PostgreSQL pelo percurso HTTP. Não foi necessária alteração no esquema produtivo.
- A porta 55109 não pôde ser utilizada no Windows; o laboratório passou a usar 5189. Não houve alteração de portas da configuração normal do produto.
- O primeiro executor restrito ficou sem resposta e foi encerrado após concluir a rodada principal. As execuções registradas ocorreram com acesso aos recursos locais.
- Dois ajustes de automação precederam a rodada final: o seletor do campo Estratégia e o nome real request_count. São ajustes do teste, não defeitos atribuídos à aplicação.

## Limites e acompanhamento

Não restam os quatro defeitos confirmados neste registro. Continuam oito avisos de depreciação das bibliotecas de testes: Starlette/httpx e configuração Alembic. A atualização de dependências deve ser feita com regressão separada. O motor reside na API; retomada automática após queda do processo não foi implementada. Ampliar campanha com modelos aprovados, recall em teste reservado e uso em resoluções adicionais permanece trabalho posterior. A comparação funcional desta sprint usa fallback e não demonstra superioridade da IA.
