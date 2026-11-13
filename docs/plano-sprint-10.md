# Sprint 10 - Release Candidate

Base revisada em 13/11/2026: main `cc9984f`, após os PRs da Sprint 09.
Integração local: `chore/s10-release-candidate`.

## Diagnóstico inicial

A Sprint 09 registrou 167 testes backend, 11 testes frontend, 17 verificações
de percurso e recuperação dos dados após reiniciar a API. Corrigiu consentimento
coercível, mensagens com JSON null, contexto de endpoints e carregamento com
período inválido. Seus registros e evidências permanecem históricos.

Pendências para a RC: estabilizar interrupção do motor; verificar o esquema real
contra migrations/ORM; documentar contratos e exemplos das APIs; padronizar
estados e orientação da interface; atualizar instalação, operação e limites.

## Branches e critérios

| Branch de tarefa | Escopo | Aceite |
|---|---|---|
| `fix/s10-estabilidade-execucoes` | Ciclo de vida e recuperação operacional | Interrupções não deixam execução ativa sem processo; sem replay de tráfego |
| `chore/s10-banco-validacao-final` | Esquema, constraints e migrations | Banco descartável íntegro, sem drift e com histórico preservado |
| `docs/s10-contratos-api` | OpenAPI, respostas, exemplos e exportação | Contrato reproduzível e documentado para todas as rotas |
| `fix/s10-interface-final` | Estados, contexto, acesso e responsividade | Fluxos coerentes e regressões verificadas |
| `docs/s10-guia-release-candidate` | README, operação e fechamento | Instruções reproduzíveis, versões e pendências explícitas |

As branches de tarefa partem da integração local e são incorporadas com merges
explícitos; dependências e resultados ficam registrados no relatório. Commits
separam reprodutores, correções, contratos e documentação quando isso facilita a
revisão. Não são criados commits vazios ou divisões artificiais.

## Limites

Sem nova funcionalidade fora do MVP ou alegação de ganho da IA sem medição. Os
integrantes já identificados no README serão preservados, sem inventar matrículas,
aprovações de banca ou atribuições individuais. Testes utilizam alvos autorizados
e banco descartável. Publicação e abertura de PR dependem de solicitação posterior.
