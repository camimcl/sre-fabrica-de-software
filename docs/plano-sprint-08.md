# Sprint 08 - consolidação, permissões e usabilidade

Base: `597677f` (main com a Sprint 07), em 02/11/2026.
Branch: `sprint-08-consolidacao-permissoes-usabilidade`.

## Critérios da entrega

1. Concluir os fluxos previstos: cadastro, cenários, execução, controle/IA local,
   relatórios, comparações, consultas, exportações e histórico.
2. Verificar a matriz de permissões na API, inclusive chamadas diretas sem passar
   pela interface. O Visualizador consulta o ambiente e gerencia somente a própria
   conta; QA administra usuários e modelos, e só modifica projetos que possui.
   O ambiente continua compartilhado, conforme o MVP; não há isolamento multi-tenant.
3. Completar edição e exclusão de cenários na interface, acesso às exportações de
   comparação, clareza dos filtros, estados vazios e explicações de acesso.
4. Revisar autorização do alvo, snapshots, transições, relatórios e auditoria.

## Sequência de implementação

- Registrar escopo e critérios antes das alterações.
- Completar auditoria de cenários e de alterações de acesso.
- Cobrir acessos permitidos e negados por perfil/proprietário.
- Completar gerenciamento de cenários na interface.
- Integrar exportações e tornar falhas de download compreensíveis.
- Revisar consultas, filtros, gráficos e navegação.
- Executar testes e build; registrar resultados e limitações reais.

Os commits são locais, separados por responsabilidade. Esta entrega não autoriza
push nem criação de PR. Metas experimentais, como recall mínimo e ganho da IA,
continuam dependendo de dados e medições; funcionalidade implementada não equivale
a meta experimental atingida.
