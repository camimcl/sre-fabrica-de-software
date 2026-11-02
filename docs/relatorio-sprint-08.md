# Relatório técnico - Sprint 08

Data: 02/11/2026. Base: `597677f`, main com o PR 6 da Sprint 07 integrado.
Branch local: `sprint-08-consolidacao-permissoes-usabilidade`.
Versão do produto: 0.8.0. Não houve push nem criação de PR nesta entrega.

## 1. Consolidação do escopo funcional

| Fluxo previsto | Implementação integrada | Verificação |
|---|---|---|
| Autenticação e contas | Cadastro público como Visualizador; login, perfil e administração QA | `test_api.py`, `test_sprint08_permissions.py` |
| Projetos e endpoints | CRUD com propriedade e registro da autorização do alvo | `test_api.py`, `test_load_tests_api.py` |
| Cenários | Criação, consulta, edição e exclusão; timeout ajustável pela interface | `SprintFivePanel.tsx`, testes da API e snapshots |
| Execução e parada | Motor HTTP real, limites, autorização explícita, snapshot imutável e cancelamento | `test_load_tests_integration.py`, `test_load_engine.py` |
| Inteligência e controle | Preparação temporal, treinamento local, meta de recall para aprovação, inferência e fallback | `test_intelligence.py`, `test_control_contract.py` |
| Histórico e relatórios | Relatório individual e comparação persistida de três estratégias, com condições equivalentes e repetições | `test_reports.py` |
| Dashboard e consultas | Dados persistidos, pesquisa, situação, estratégia, período e paginação | `test_sprint07.py`, testes do frontend |
| Exportação | CSV da consulta e CSV/PDF da comparação acessíveis pela interface; PDF individual com orientação se ainda não gerado | `test_sprint07.py`, `frontend/tests/sprint08.test.mjs` |
| Rastreabilidade | Auditoria transacional de projetos, endpoints, cenários, contas e transições de execução | `test_sprint07.py`, `test_sprint08_permissions.py` |

Os recursos já implementados foram preservados. A Sprint 08 completa as lacunas
de operação pela interface e revisa os contratos. Nenhuma funcionalidade do MVP
foi removida. Continuam fora do MVP, conforme README: execução distribuída,
multi-tenancy, APIs externas de IA, GPU, aplicativo móvel e cobrança.

O funcionamento da IA e a meta experimental são questões distintas. A aplicação
mantém o fallback quando não existe modelo aprovado e bloqueia aprovação abaixo
da meta de recall. Esta entrega não afirma que o recall medido atingiu 0,80 nem
que AI_HYBRID superou as demais estratégias em uma campanha real.

## 2. Matriz de permissões revisada

O MVP possui um ambiente compartilhado: usuários autenticados consultam os projetos
e resultados. A propriedade restringe alterações, não transforma o ambiente em
uma solução multi-tenant.

| Operação | Visualizador | QA de outro projeto | QA proprietário |
|---|---|---|---|
| Consultar projetos, cenários, métricas, previsões e relatórios | Permitido | Permitido | Permitido |
| Consultar dashboard e exportar dados existentes | Permitido | Permitido | Permitido |
| Criar projeto próprio | Negado | Permitido | Permitido |
| Alterar/excluir projeto, endpoint ou cenário | Negado | Negado | Permitido |
| Criar, iniciar, cancelar, concluir ou falhar execução | Negado | Negado | Permitido, respeitando o ciclo de vida |
| Gerar relatório ou comparação do projeto | Negado | Negado | Permitido, respeitando os critérios |
| Treinar/aprovar modelos globais | Negado | Permitido | Permitido |
| Listar/administrar usuários e consultar auditoria global | Negado | Permitido | Permitido |
| Editar/excluir a própria conta | Permitido, sem promover o próprio perfil | Permitido, com restrições do último QA e dependências | Permitido, com as mesmas restrições |

As negações são aplicadas pela API, mesmo em chamadas diretas. Os novos testes
executam mutações por Visualizador e por QA não proprietário e verificam HTTP 403,
sem alterar a execução. Requisições sem autenticação às consultas retornam 401.
Uma alteração de perfil passa a valer nas chamadas seguintes, inclusive para um
token já emitido, pois a API consulta o perfil persistido.

A proteção do último QA passou a bloquear as linhas dos QAs durante a transação
no PostgreSQL. O teste concorrente dispara duas despromoções simultâneas: uma
recebe 200, outra 409, e o banco permanece com um QA.

## 3. Melhorias de usabilidade

- Cenários: editar, excluir com confirmação, cancelar edição, ajustar timeout e
  conferir concorrência inicial versus máxima antes de salvar.
- A edição explica que afeta novas execuções; os snapshots antigos permanecem.
  Exclusão de cenário com execuções vinculadas continua bloqueada pelo banco.
- Comparações: botões de exportação CSV/PDF junto ao resultado selecionado.
- Downloads: mensagem informa quando solicitar a geração do relatório ao QA;
  execuções pendentes ou em andamento não oferecem PDF ativo.
- Consultas: limpar filtros, validação de intervalo invertido e período convertido
  do calendário local para UTC, incluindo o último milissegundo do dia.
- Dashboard: ponto visível mesmo quando existe somente um dia; valores também
  apresentados como texto. O agrupamento diário em UTC é identificado.
- Auditoria: esclarece que a lista é global ao ambiente e exclusiva de QA;
  detalhes históricos que não são JSON não interrompem a renderização.
- Navegação: respostas antigas de projeto/aba são descartadas; formulários de
  endpoint/projeto são limpos ao trocar de contexto e no logout.
- A interface explica as restrições por perfil e propriedade e identifica a
  versão atual como Sprint 08, sem os rótulos de entrega antigos nos módulos.

## 4. Revisão das regras de negócio

**Autorização antes da execução.** O campo `authorization_acknowledged` agora é
obrigatório, booleano estrito e verdadeiro. Antes, omitir o campo podia produzir
uma execução pendente com o valor padrão falso, pois o validador não era aplicado
ao default. A API rejeita ausência, falso, texto e número sem persistir execução.
A autorização e a configuração do endpoint continuam revalidadas no início.

**Histórico imutável.** Alterar um cenário não modifica configurações nem alvo
das execuções já criadas. O novo teste confere o snapshot antes e depois da edição.

**Auditoria atômica.** Edição/exclusão de cenário e criação/edição/exclusão de conta
geram histórico na mesma transação da ação. Duplicidade de e-mail não deixa um
evento de criação parcial. O log não contém senha, hash ou token; alteração de
senha é registrada somente como um indicador booleano. O ator pode ficar nulo
após exclusão da própria conta, conforme a FK `ON DELETE SET NULL`.

**Ambiente reproduzível.** Versões do projeto e locks foram alinhados em 0.8.0.
O conjunto científico permanece NumPy 1.26.4, SciPy 1.13.1 e scikit-learn 1.5.2.
O suporte a Python 3.11 e 3.12 foi explicitado para evitar instalação em versões
sem compatibilidade com essas dependências. A auditoria npm identificou Vite
7.3.6 afetado; a atualização para 7.3.7 resultou em zero vulnerabilidades
reportadas pelo registro na consulta de 02/11/2026.

## 5. Evidências e reprodução

O [índice de evidências](evidences/sprint-08/README.md) registra os resultados
finais. Foi utilizado um PostgreSQL 16 descartável em porta própria; os serviços
e volumes de desenvolvimento não foram substituídos. As migrations foram
aplicadas antes dos testes de integração.

Resultado final: **125 testes de backend aprovados, zero falhas e zero skips**;
**quatro testes de frontend aprovados**; compilação TypeScript/Vite e duas imagens
Docker construídas. Há oito avisos de depreciação de bibliotecas de teste, sem
falhas. A consulta final da auditoria npm reportou zero vulnerabilidades.

Backend, em Python 3.11/3.12, a partir de `backend/`:

```text
uv sync --locked --extra dev --no-install-project
uv run --no-sync alembic upgrade head
uv run --no-sync pytest -q tests --junitxml=../docs/evidences/sprint-08/pytest-postgres-locked.xml
```

Configure `DATABASE_URL` e `LOADFORGE_TEST_DATABASE_URL` exclusivamente para um
banco descartável cujo nome termine em `_test`. Os testes de migration e
concorrência isolam seus próprios schemas e removem apenas esses schemas.

Frontend, em Node 22.18+ ou 24, a partir de `frontend/`:

```text
npm ci
npm test
npm run build
npm audit
```

O workflow passa a executar também os quatro testes do frontend. O CI remoto não
foi disparado nesta entrega local. Os builds Docker foram verificados com as
dependências fixadas. Não foi realizada uma nova sessão interativa de navegador;
a evidência desta rodada é de testes HTTP, concorrência, persistência, testes do
frontend e compilação, sem alegação de novos prints de usabilidade.

## 6. Dificuldades e próximos passos

A cópia local estava na Sprint 06 e foi necessário atualizar a referência da main
antes de iniciar, preservando a branch anterior. A autenticação SSH estava
indisponível; a leitura da versão pública foi feita por HTTPS, sem alteração do
endereço de envio e sem push. O ambiente Python local tinha bibliotecas diferentes
do lock; a verificação final usou um ambiente separado com os locks sincronizados.

Próximos passos: revisão humana da branch; demonstração visual dos perfis e dos
fluxos; campanha experimental ampliada com modelo aprovado; avaliação de recall
com teste reservado; e tratamento futuro dos avisos de depreciação das bibliotecas
de testes. Não há migração para multi-tenancy nem alegação de isolamento por equipe.

Repositório: https://github.com/camimcl/sre-fabrica-de-software
