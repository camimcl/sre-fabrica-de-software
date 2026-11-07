# Arquitetura do LoadForge

O MVP adota um monólito modular para manter o fluxo de execução, métricas, inferência e controle no mesmo processo de aplicação, com responsabilidades internas separadas. O PostgreSQL persiste o histórico; o modelo de IA é carregado localmente; e o motor de carga somente utiliza endpoints cuja autorização esteja registrada.

## Módulos

- `auth`: usuários e papéis.
- `projects`: projetos e endpoints autorizados.
- `load_tests`: cenários e execuções.
- `metrics`: janelas temporais e métricas agregadas.
- `intelligence`: características, versões e previsões do modelo local.
- `control`: estratégias fixa, por regras e assistida por IA.
- `reports`: consolidação e comparação das execuções.

As decisões arquiteturais estão registradas em `decisions/`. Os diagramas editáveis e exportados ficam em `docs/diagrams`.

## Como ler a arquitetura

O diagrama oficial foi dividido em três faixas. A primeira mostra o acesso e a execução somente contra um alvo autorizado; a segunda apresenta o ciclo adaptativo `métricas → IA local → controle híbrido → nova concorrência`; a terceira concentra cadastros, artefato do modelo, relatórios e PostgreSQL. As setas seguem trajetos ortogonais, e as cores distinguem aplicação, IA, otimização e dados.

Os diagramas de classes e dados seguem a mesma regra: somente os relacionamentos principais recebem linhas. As referências secundárias continuam explícitas como atributos UUID ou chaves estrangeiras dentro das tabelas. O guia completo está em `docs/diagrams/README.md`.

## Estado verificado na Sprint 09

React/TypeScript é servido por Nginx, que encaminha `/api` à FastAPI. SQLAlchemy e Alembic gerenciam 13 tabelas no PostgreSQL 16. O módulo `audit` registra operações na mesma transação das mutações; a leitura global exige QA. O motor assíncrono permanece no processo da API: reiniciar esse processo não é um mecanismo de retomada de carga em andamento. As métricas são persistidas em janelas nominais de 2 s e a previsão usa cinco janelas futuras. Artefatos locais passam por hashes e aprovação; ausência/falha do modelo aciona regras e registra a causa.

As correções da Sprint 09 não alteram tabelas: tornam a confirmação de autorização estrita e protegem a interface contra respostas de contextos antigos e erros HTTP nulos. Veja o [modelo atualizado](../diagrams/README.md) e o [relatório de verificação](../relatorio-sprint-09.md).
