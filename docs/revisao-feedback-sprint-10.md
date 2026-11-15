# Revisão dos feedbacks da Sprint 10

Data: 15/11/2026. Foram lidas as conversas e revisões dos PRs #22 a #28,
incluindo as threads inline, e o PR #29 citado pela revisão. Nenhuma thread
inline adicional foi encontrada. As alterações abaixo são exclusivamente
locais: sem push, respostas, resolução de conversas ou mudança de estado dos PRs.

| PR | Solicitação | Atendimento local |
|---|---|---|
| #22 | Aplicar `4f59bc6` para entregar SIGTERM ao Uvicorn | Commit incorporado na própria branch de estabilidade. Já estava na RC; não foi duplicado nela. |
| #23 | Detectar PK ausente e testar com rollback | Comparação explícita das colunas ordenadas das PKs do PostgreSQL com o ORM. Teste remove `operation_logs_pkey`, confirma ausência, exige rejeição e restaura por rollback. |
| #24 | Documentar os dois formatos do 422 e o acesso QA em GET /users | `anyOf` para lista de erros e detalhe textual nas quatro operações com período. Testes HTTP exercitam data inválida e intervalo invertido em consulta, dashboard, auditoria e CSV; teste de permissão de usuários. OpenAPI e referência regenerados. |
| #25 | Incorporar os seletores em português do #29 | Commit original de Camile incorporado na branch de interface e na RC, preservando autoria e verificações dos códigos da API. |
| #26 | Aprovado sem pedido de mudança | Mantido sem alterações. |
| #27 | Aplicar `a867a57` para preservar os hashes | Commit incorporado na branch de documentação. Manifestos conferidos contra bytes lidos por `git show`, tanto nessa branch quanto na RC. |
| #28 | Reunir #29, correção de PK e contrato 422/QA | Todas incorporadas na branch consolidada, sem nova publicação. |

## Reprodutor do banco

Em banco descartável terminado em `_test`, a remoção transacional da PK de
`operation_logs` produziu inicialmente três aprovações e uma falha: o validador
retornava `ok: true`. O novo caso falhou antes da correção, reproduzindo o
feedback. O bloco `finally` faz rollback inclusive em falha de asserção.
A implementação verifica todas as PKs, incluindo ordem e conjunto de colunas;
não apenas o nome da constraint reproduzida. Não houve migration nem alteração
do banco de demonstração para corrigir esse defeito do validador.

## Contrato e navegação

As respostas reais 422 são confrontadas com as alternativas declaradas no
OpenAPI. Os exemplos e o snapshot completo continuam cobertos pelos testes.
`GET /users` documenta QA e recusa o Visualizador pela API real. A referência
gerada mantém a identificação de versão correspondente à branch de destino.

O ajuste do PR #29 limita-se aos rótulos exatos Concluída, Em execução e
Cancelada no monitor; os códigos COMPLETED e CANCELLED continuam verificados
na API. A revisão de Camile registra 17 casos de navegação e dois de
concorrência aprovados com esse ajuste. Esse resultado é atribuído à revisão,
não apresentado como nova execução desta rodada. Aqui foi conferida também
a sintaxe JavaScript do roteiro incorporado.

## Evidências históricas e publicação

Verificação desta rodada: **197 testes backend aprovados**, zero falhas, erros
ou skips, em 181,94 s, com um aviso remanescente de TestClient/httpx.
Os dez casos acrescentados correspondem à PK e às respostas/permissões reais
da API. Frontend: **14 testes aprovados** e build TypeScript/Vite concluído.
Também passaram a sintaxe do roteiro JavaScript, a referência OpenAPI gerada,
`git diff --check` e a conferência dos hashes versionados. O JUnit desta rodada
está em `docs/evidences/sprint-10-revisao/pytest.xml`.

Os resultados de 13/11 e o documento Word permanecem históricos e não foram
reescritos para simular uma nova execução. A correção de bytes de #27 foi
conferida diretamente nos objetos Git; os hashes correspondem ao conteúdo
versionado. As branches locais dos PRs foram corrigidas separadamente para
que uma futura publicação possa atualizar cada escopo sem depender apenas
do PR consolidado.

O bloqueio de faturamento do CI informado pela revisão depende do responsável
pela conta. Nenhum check foi removido, contornado ou executado novamente no
GitHub, e nenhuma aprovação humana foi presumida.
