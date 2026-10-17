# feat(sprint-06): integrar relatórios experimentais e fortalecer evidências

## Resumo

Implementa o terceiro módulo do LoadForge — histórico e relatórios comparativos — integrado aos projetos, cenários, execuções, métricas e controle. A entrega trata primeiro o feedback da Sprint 05 e depois evolui interface, navegação e avaliação experimental da Sprint 06.

A branch foi atualizada sobre a `main` com o PR #4 de CI. O workflow existente foi preservado, e os lockfiles acompanham a versão `0.6.0`.

## Feedback da Sprint 05

- Formaliza o cronograma revisado, registrando a antecipação da IA e do controlador e o foco experimental da Sprint 06.
- Introduz balanceamento de classes e calibração do limiar de classificação exclusivamente na validação, mantendo divisão cronológica com expurgo do horizonte futuro e teste reservado à avaliação final.
- Prioriza candidatos que atinjam recall de `0,80` e bloqueia a aprovação de modelos cujo recall registrado esteja abaixo da meta.
- Persiste o limiar no artefato e os metadados de avaliação para auditoria; a inferência usa o limiar versionado.
- Preserva o resultado histórico: recall `0,70370` e F1 `0,82609`. As mudanças não são apresentadas como prova de que um novo modelo real já atingiu a meta.

## Terceiro módulo e integração

- Histórico de execuções por projeto e relatórios individuais calculados das janelas persistidas.
- Comparação de `FIXED`, `RULES` e `AI_HYBRID`, exigindo execuções concluídas, pelo menos três repetições por estratégia, quantidades iguais e condições equivalentes.
- Estatísticas de throughput, latência, erro e conformidade: média, desvio-padrão populacional, mínimo e máximo, além de deltas da IA híbrida contra as duas referências.
- Persistência da comparação, condições, impressão SHA-256 e vínculos com as execuções usadas.
- Consulta por usuários autenticados; geração restrita ao QA proprietário do projeto.

## Correções da verificação final

- Registra o alvo efetivamente carregado pelo motor antes do tráfego: endpoint, URL, método HTTP e duração nominal das janelas. A comparação deixa de depender do cadastro mutável do cenário.
- Rejeita novas comparações com históricos sem snapshot, sem inventar informações retroativas. Relatórios anteriores continuam consultáveis.
- Audita janelas com inferência, fallback por regras e ausência de comprovação, identificando versões dos modelos. Resultados com fallback ou modelos não uniformes não são atribuídos exclusivamente à IA.
- Esclarece que a latência comparativa é a média dos P95 das janelas, não o P95 global; throughput considera o tempo observado das janelas.
- Alinha constraints e índice das entidades de comparação ao esquema migrado.
- Amplia testes para mudanças de alvo, históricos incompletos, fallback, permissões, entrada inválida e persistência após reconexão.

## Interface e navegação

- Navegação entre Projetos, Testes, Relatórios e Usuários, mantendo seleção de projeto nas áreas dependentes de contexto.
- Histórico filtrável, seleção de execuções, contagem balanceada e recuperação de comparações salvas.
- Exibição de deltas, dispersão, condições, identificadores das execuções e auditoria de IA/fallback.
- Mensagens de validação com campos e motivos; meta de recall e limiar apresentados junto ao modelo.
- Proteção contra respostas atrasadas após troca de contexto, bloqueio de operações simultâneas e limite de 90 execuções por comparação.

## Banco e atualização

As migrations `20261015_0005` e `20261016_0006` acrescentam as tabelas comparativas e o snapshot do alvo, respectivamente. O esquema SQL e os diagramas-fonte foram atualizados.

Aplicar `alembic upgrade head` antes de iniciar o backend atualizado. A nova coluna é opcional para preservar o histórico. Execuções antigas sem snapshot precisam ser refeitas para participar de novas comparações verificáveis. Não é necessário excluir dados existentes.

## Verificação realizada em 16/10/2026

- **77 testes aprovados, zero falhas e zero ignorados**, com PostgreSQL 16 descartável.
- Migrações até `20261016_0006`, preservação de histórico e rejeição de limites históricos incompatíveis verificadas.
- Nove execuções HTTP reais contra alvo local, em ordem rotativa, integradas à comparação e consulta posterior.
- Relatório e nove vínculos recuperados após fechar e reabrir a conexão PostgreSQL.
- Suíte de relatórios novamente aprovada após as últimas asserções: **10 testes**, incluindo respostas 401, 403, 404 e 422.
- TypeScript e build Vite aprovados; builds Docker da API e do frontend aprovados.
- Instalação limpa do frontend reportou zero vulnerabilidades; `source-map-js` atualizado para `1.2.2`.
- Evidências em `docs/evidences/sprint-06/`; metodologia e limitações em `docs/relatorio-sprint-06.md`.

O banco e os contêineres existentes de desenvolvimento não foram alterados. A suíte local usa Python 3.12; a imagem da API usa Python 3.11. Avisos de depreciação de TestClient/httpx e Alembic permanecem sem falhas. Esta revisão não incluiu nova inspeção visual no navegador nem execução remota do workflow do GitHub.

## Limitações e próxima evidência necessária

O teste HTTP integrado usa fallback, sem modelo aprovado. Ele comprova integração e persistência, **não superioridade da IA**. Os valores da fixture também não são resultados de desempenho real.

Ainda é necessário registrar um novo treino com dados representativos e uma campanha controlada com modelo aprovado, três ou mais repetições equivalentes por estratégia, versão do alvo, ordem, condições ambientais e análise da dispersão. Portanto, não se afirma que o recall real já superou `0,80` nem que `AI_HYBRID` apresentou ganho comprovado. A calibração do classificador também não altera, por si só, os limites de risco do controlador.

## Roteiro de revisão

1. Aplicar as migrations e entrar como QA proprietário.
2. Confirmar o alvo autorizado e executar cenários equivalentes nas três estratégias.
3. Selecionar as execuções em Relatórios, gerar a comparação e conferir condições, estatísticas, deltas e auditoria de fallback.
4. Recarregar e recuperar a mesma comparação para demonstrar persistência.
5. Confirmar que seleções incompletas, incompatíveis ou sem snapshot são rejeitadas e que visualizadores apenas consultam.
