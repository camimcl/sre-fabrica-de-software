# Checklist de entrega — Sprint 02

## Arquitetura e modelagem

- [x] Arquitetura do monólito modular documentada.
- [x] Integração entre motor de carga, métricas, IA local e controlador adaptativo explicitada.
- [x] Diagrama de classes com entidades, serviços e interfaces.
- [x] MER com entidades e cardinalidades.
- [x] Modelo relacional alinhado à migration e ao `database/schema.sql`.
- [x] Diagramas reorganizados por faixas, com ligações ortogonais e sem sobreposição central.
- [x] Relações secundárias documentadas nos atributos e nas chaves estrangeiras para preservar legibilidade.

## Protótipo

- [x] Arquivo editável criado no Figma.
- [x] Fluxos de autenticação, cadastro autorizado, cenário, execução, parada e histórico modelados.
- [x] Monitoramento apresenta risco previsto e decisões do controlador.
- [x] Telas de relatório comparativo e versões do modelo incluídas no arquivo.
- [x] Link e capturas registrados em `docs/prototypes/`.

## Banco e repositório

- [x] PostgreSQL 16 definido no Docker Compose com volume e healthcheck.
- [x] Serviço `migrate` criado para aplicar Alembic após o banco ficar saudável.
- [x] Dez tabelas implementadas no esquema inicial.
- [x] Migration reversível e seed de desenvolvimento adicionados.
- [x] Contratos do preditor e do controlador criados.
- [x] Testes estruturais do esquema, migration, settings e fallback adicionados.
- [x] README atualizado com escopo, IA, arquitetura e procedimento Docker.

## Documento

- [x] Diagramas e telas acompanhados de explicação e legenda.
- [x] Link do GitHub e do Figma incluídos.
- [x] Relatório técnico da Sprint 02 disponível em `docs/relatorio-sprint-02.md`.
