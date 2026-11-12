# Sprint 09 - verificação integral e preparação da entrega

Grupo 21 - LoadForge | Responsável pelo registro de QA/PO: Camile Marcele Pereira de Araújo.
Prazo: 07/11/2026. Base de análise: `f9a62fb`, integração da Sprint 08. Planejamento registrado em 06/11/2026.

## Objetivo e abordagem

Como QA e PO, organizei a verificação por risco: autenticação e autorização, integridade dos cadastros, execução de carga, IA/controle, relatórios, consultas, exportações e continuidade da navegação. Diferencio testes automatizados, observações de navegador e metas experimentais. Um resultado esperado só será marcado como obtido quando houver execução e evidência associada.

As 81 páginas recebidas consolidam as Sprints 01–08. O complemento da Sprint 09 será anexado, sem reescrever o histórico. O relato final terá casos identificados, pré-condições, procedimentos, esperado/obtido, bugs, correções, retestes, dificuldades e pendências.

## Divisão da entrega

| Tarefa | Responsabilidade de referência | Entregável verificável |
|---|---|---|
| S09-01 Planejamento e rastreabilidade | Camile, QA/PO; Emerson, coordenação | Plano, matriz de testes e fluxo de branches por tarefa. |
| S09-02 Funcional e validação HTTP | Camile, QA; Aline/Emerson, backend | Casos positivos/negativos de autenticação, CRUD, regras, acesso e erros; resultados automatizados. |
| S09-03 Persistência e ambiente | Ricardo, dados/infraestrutura | Banco descartável, migrations, testes reais de PostgreSQL e evidências de recuperação. |
| S09-04 Navegação e experiência | Camile, QA; Cayo, frontend | Percursos reais de perfis, troca de contexto, formulários, execução, relatórios, downloads e capturas explicadas. |
| S09-05 Correções e regressão | Responsável pelo módulo, com reteste QA | Um registro por bug confirmado, teste reprodutor e correção verificável. |
| S09-06 Documentação e entrega | Camile, QA/PO; Ricardo, documentação; Emerson, envio | Relatório técnico, evidências, roteiro manual e PDF único incremental identificado. |

A divisão indica responsabilidades de revisão e apresentação; não atribui horas, execução manual ou autoria individual que não estejam comprovadas. O Scrum Master coordena o envio único no Teams.

## Critérios de verificação

- Funcionais: criação, consulta, atualização e exclusão dos cadastros; sessão; cenário; execução e cancelamento; controle/IA; relatório/comparação; dashboard; auditoria e exportação.
- Validação: obrigatoriedade, espaços em branco, formatos, limites, duplicidade, autorização explícita, relações entre campos e estados incompatíveis. Conferir código HTTP, mensagem e ausência de efeito indevido.
- Navegação: perfis QA proprietário, QA não proprietário e Visualizador; troca de projeto; retorno às áreas; atualização/recarregamento; formulário e resposta atrasada; mensagens e downloads.
- Persistência: testes sobre banco `_test` isolado e serviços de demonstração próprios, sem limpeza do banco de desenvolvimento.
- Regressão: executar suítes existentes e novos casos, registrar falhas iniciais, correções e resultado final sem omitir testes ignorados.
- Documentação: verificar arquitetura, esquema/migrations, regras, instruções e links; atualizar somente o que divergir do código. Preservar metas experimentais ainda não comprovadas.

## Política de evidências

Logs e capturas serão identificados em `docs/evidences/sprint-09/`. Credenciais e tokens não integram evidências públicas. Os casos determinísticos de IA comprovam contratos; não comprovam generalização ou ganho em produção. Não serão enviados testes de carga a serviços externos. O roteiro da apresentação utilizará exclusivamente o alvo local autorizado.

## Gestão de mudanças

A partir desta entrega, o fluxo é por tarefa, conforme [guia de contribuição](../CONTRIBUTING.md). Correções serão abertas somente depois de confirmar um defeito. Os commits registram mudanças coerentes, não divisões artificiais para aumentar contagem. O relatório final relacionará branches, dependências e commits efetivamente produzidos.
