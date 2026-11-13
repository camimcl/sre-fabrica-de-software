# Relatório técnico - Sprint 10

Data: 13/11/2026. Produto: LoadForge 1.0.0-rc.1.
Base revisada: `main` em `cc9984f`, incluindo as entregas da Sprint 09.
Integração local: `chore/s10-release-candidate`. Não foi feito push nem aberto PR
nesta sprint; a publicação fica para solicitação posterior.

## Revisão da base e problemas encontrados

A Sprint 09 integrou os módulos e corrigiu coerção do consentimento de alvo,
tratamento de erros HTTP nulos, troca de contexto dos endpoints e carregamento
com intervalo inválido. Seus testes/evidências permanecem preservados. A revisão
da RC concentrou-se em ciclo de vida do motor, esquema, contratos, interface e
instruções de operação, sem redesenhar módulos já aprovados.

Foi reproduzida uma tarefa do motor cancelada sem persistir estado terminal.
Também foram encontrados oito índices já migrados que não apareciam nos
metadados ORM, documentação de downloads sem o tipo real CSV/PDF, identificação
visual ainda em Sprint 08 e um modelo sintético de teste registrado na base ORM
da aplicação. As correções e verificações são rastreáveis nos commits de tarefa.

## Atendimento aos requisitos

| Requisito | Entrega |
|---|---|
| Sistema estável | Encerramento do motor, registro de cancelamento forçado, recuperação idempotente de execuções interrompidas, auditoria e exclusividade da API por banco; regressão dos módulos anteriores |
| Interface final | Versão RC, nomes de situações/estratégias em português, mensagens de sessão/permissão, motivo de encerramento, foco visível, contraste, apresentação das consultas e ajustes para telas estreitas |
| Banco final | PostgreSQL 16 no head `20261020_0007`; 13 tabelas, 33 CHECKs esperadas; índices ORM alinhados às migrations; CLI de verificação sem alteração de dados e testes de divergência com rollback |
| APIs documentadas | OpenAPI exportável e versionado, referência completa gerada, Swagger/ReDoc, exemplos validados, autenticação, matriz de acesso, parâmetros, erros e formatos de download |
| README atualizado | Nome/objetivo, tecnologias, pré-requisitos, instalação/configuração, banco, execução Docker/local, estrutura, links e equipe existente preservada |

O motor continua no processo da API: a RC exige um worker por banco. A posse
exclusiva usa advisory lock PostgreSQL; um segundo runtime gerenciado é recusado.
No desligamento normal, novas requisições param e as em voo são drenadas. No
startup após queda, RUNNING remanescentes tornam-se FAILED com motivo/data e
auditoria. Históricos são preservados e tráfego nunca é retomado automaticamente.
O Compose encaminha sinais diretamente ao Uvicorn com `exec`.

## Documentação e banco

O [guia de API](api/README.md), a [referência gerada](api/referencia.md) e o
[contrato OpenAPI](api/openapi.json) cobrem as operações públicas e protegidas.
Os testes conferem exemplos contra os schemas reais e a igualdade do contrato
exportado com `app.openapi()`. O CI também verifica referência e banco.

Não foi criada migration vazia: os índices corrigidos nos metadados já existiam
na migration aplicada. `check-db` verifica o contrato final e acusa diferenças;
testes removem temporariamente uma CHECK e um índice e comprovam detecção e
restauração por rollback. O [guia operacional](release-candidate.md) descreve
instalação, atualização, cópias de segurança, recuperação e limites.

## Verificação e evidências

- Backend: **187 testes aprovados**, sem falhas, erros ou skips; PostgreSQL 16
  para testes específicos de migrations/lease/esquema, além das fixtures SQLite
  isoladas dos testes de API/motor. Duração da rodada final: 161,23 s.
- Um aviso remanescente de Starlette sobre a integração de TestClient com httpx;
  as dependências fixadas foram preservadas. Os avisos Alembic de separador de
  caminhos foram eliminados com configuração explícita e portátil.
- Frontend: **14 testes aprovados**, compilação TypeScript e build Vite 7.3.7
  concluídos. `npm ci` no build Docker registrou zero vulnerabilidades na
  consulta daquela execução; isso não equivale a auditoria completa do produto.
- Navegação real: Projetos → Execuções → Relatórios → Dashboard → Consultas →
  Operações; estados traduzidos, comparação recuperada e filtro combinado com
  três registros. Dashboard sem overflow horizontal nas larguras 320 e 360.
- Resultados do percurso HTTP e do teste de recuperação são registrados no
  [índice de evidências](evidences/sprint-10/README.md), com suas limitações.

Os ensaios comparativos curtos usam alvo Docker próprio, concorrência pequena e
três repetições por estratégia. Comprovam integração, condições e avisos; não
comprovam ganho estatístico em produção nem ganho exclusivo de IA. A meta de
recall 0,80 continua sendo exigida para aprovação; nenhum modelo foi aprovado
artificialmente e os números históricos não foram reescritos.

## Organização do desenvolvimento

| Branch | Alterações principais |
|---|---|
| `fix/s10-estabilidade-execucoes` | Reprodutor, cancelamento, drenagem, recuperação e lease |
| `chore/s10-banco-validacao-final` | Índices ORM, `check-db`, configuração Alembic e testes |
| `docs/s10-contratos-api` | Contratos, exemplos, exportação OpenAPI, testes e guias |
| `fix/s10-interface-final` | Apresentação, mensagens, acessibilidade e revisão visual |
| `test/s10-isolamento-regressao` | Metadados sintéticos isolados e laboratório com limites de espera |
| `docs/s10-guia-release-candidate` | Versão RC, README, CI, operação, roteiro integrado e evidências |

As tarefas foram incorporadas por merges explícitos, preservando commits
convencionais com alterações revisáveis. O [plano](plano-sprint-10.md) e o
[cronograma](cronograma-sprints.md) registram o escopo.

## Dificuldades, escopo e próximos passos

A rodada final inicial encontrou falta de espaço em C:, causando falhas em
temporários SQLite e no Docker. O ambiente de testes do projeto foi deslocado
para D:, os temporários do laboratório passaram a ficar junto dele e a unidade
foi liberada pelo responsável. Após corrigir a interferência do modelo sintético,
a regressão completa foi repetida e aprovada. Isso foi falha de ambiente e de
isolamento de teste, não evidência de aprovação na primeira tentativa.

Não houve retirada de funcionalidade do MVP. Continuam fora do escopo execução
distribuída/alta disponibilidade, múltiplos workers, deploy público e ampliação
da IA. CPU do alvo não é medida e o fallback local documentado não deve ser
apresentado como medição real do alvo. Os limites e as medidas operacionais
estão no guia da RC.

Próximos passos: revisão pela equipe e homologação com usuários; repetir campanha
experimental com modelos aprovados e condições representativas; ensaiar
backup/restauração na infraestrutura final; validar apresentação e, após
autorização, publicar a branch e abrir o PR. Atualizações da biblioteca de testes
devem ser tratadas em revisão própria, com nova regressão.

Os nomes e papéis da equipe já constavam no README e foram preservados. Não foram
inventados matrículas, assinaturas, aceite da banca, datas de apresentação ou
endereço de implantação que não foram fornecidos. Repositório oficial:
[GitHub do LoadForge](https://github.com/camimcl/sre-fabrica-de-software).
