# Evidências da Sprint 06

Data da verificação local: 16/10/2026, após rebase sobre o merge do PR #4.

## Evidências reproduzíveis já disponíveis

| Verificação | Resultado |
|---|---|
| Backend final | [Relatório JUnit final](pytest-final.xml): 77 testes aprovados, zero falhas e zero ignorados, incluindo PostgreSQL 16. O [registro anterior](pytest-local.xml) permanece como histórico. |
| Frontend | TypeScript e build Vite de produção aprovados. |
| Contêineres | Builds `loadforge-api:sprint06-final` (Python 3.11) e `loadforge-frontend:sprint06-final` (Node 22/Nginx) aprovados, sem substituir serviços em uso. |
| Dependências frontend | `source-map-js` atualizado de `1.2.1` para `1.2.2`; auditoria npm final com zero vulnerabilidades conhecidas. |
| Comparação | Fixture automatizada com 3 estratégias × 3 repetições valida equivalência, dispersão, deltas e persistência. |
| API integrada | Nove execuções HTTP reais locais, ordem rotativa, comparação, histórico e recuperação aprovados; sem modelo aprovado, com fallback explicitamente auditado. |
| Persistência PostgreSQL | Resultado e nove vínculos recuperados após fechar e reabrir a conexão. |
| Migração | Revisão `20261016_0006` aplicada; testes de preservação de histórico e rejeição de conflitos aprovados. |
| Segurança e validação | Suite de relatórios novamente executada: 10 testes aprovados, incluindo 401, 403, 404 e 422; visualizador consulta, mas não gera comparação. |
| Integridade experimental | Snapshot do alvo, rejeição de históricos sem snapshot, divulgação de fallback e identificação de modelos. |
| Compatibilidade com CI | `uv.lock` alinhado à versão `0.6.0`; `uv sync --locked`, `uv lock --check` e o comando pytest do workflow aprovados localmente. |

Os dados numéricos da fixture são deliberadamente controlados para testar os cálculos. O novo teste HTTP envia tráfego real apenas para localhost e confirma integração; usa fallback por regras. Nenhum desses testes demonstra que a IA superou as demais estratégias. Nesta revisão não foi realizada inspeção visual no navegador.

Comandos usados, a partir de `backend`, com `DATABASE_URL` e `LOADFORGE_TEST_DATABASE_URL` apontando exclusivamente ao banco descartável `loadforge_ci_test` na porta local 25432:

```text
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --junitxml=../docs/evidences/sprint-06/pytest-final.xml
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_reports.py
```

Frontend: `npm run build`. A suíte final usa Python 3.12 no Windows; avisos de depreciação não foram ocultados. O banco de desenvolvimento existente não foi alterado.

## Evidência experimental a coletar

A sessão de laboratório deve produzir uma comparação persistida com no mínimo nove execuções reais e registrar:

- identificador da comparação e das execuções;
- versão do alvo autorizado e condições do ambiente;
- ordem das repetições;
- médias, desvios-padrão, mínimos e máximos;
- deltas de `AI_HYBRID` contra `FIXED` e `RULES`;
- incidentes, aquecimento e repetições descartadas com justificativa;
- captura da tela antes e depois de recarregar a aplicação.

O procedimento completo está no [Relatório Técnico da Sprint 06](../../relatorio-sprint-06.md). O repositório mantém a lacuna identificada até a execução real, em vez de promover números sintéticos como evidência de desempenho.
