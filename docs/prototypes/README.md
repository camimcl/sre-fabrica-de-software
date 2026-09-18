# Protótipo inicial da Sprint 02

O protótipo foi criado no Figma para representar os fluxos principais e validar a organização inicial da interface. Ele ainda não corresponde a uma implementação React e poderá mudar durante o desenvolvimento, a validação técnica e os testes de usabilidade.

**Arquivo Figma:** [LoadForge — Protótipo Sprint 02](https://www.figma.com/design/isw6HZdCiomQvSekNScl9J)

## Telas modeladas

1. Login;
2. Dashboard;
3. Projetos e endpoints autorizados;
4. Cadastro de endpoint e evidência de autorização;
5. Configuração de novo cenário de teste;
6. Monitoramento ao vivo;
7. Confirmação de parada de emergência;
8. Histórico de execuções;
9. Relatório comparativo entre carga fixa, regras e IA com regras;
10. Versionamento e métricas dos modelos de IA.

Os arquivos em `exports/` registram o estado atual das telas para consulta e documentação. O arquivo editável e a organização completa dos quadros permanecem no Figma.

## Decisões de interface

- navegação lateral persistente para reduzir trocas de contexto;
- destaque visual para autorização e parada de emergência;
- monitoramento conjunto de métricas observadas, risco previsto e decisão do controlador;
- identificação explícita do modelo local e da latência de inferência;
- comparação experimental entre as três estratégias de controle;
- cores de estado acompanhadas de texto, sem depender apenas da cor.

O fluxo detalhado está em [`flow.md`](flow.md).
