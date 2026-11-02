# Evidências da Sprint 08

Data: 02/11/2026. Revisão de código para os testes finais: `98a799a`.
Branch: `sprint-08-consolidacao-permissoes-usabilidade`.

## Execuções finais

Resultado: **125 testes de backend aprovados, sem falhas ou skips**, e quatro
testes de frontend aprovados. Build TypeScript/Vite e ambas as imagens Docker
concluídos. Auditoria npm: zero vulnerabilidades reportadas em 02/11/2026.
Persistem oito avisos de depreciação nas bibliotecas de testes, sem falhas.

- `pytest-postgres-locked.xml`: suíte completa com PostgreSQL 16 e dependências
  fixadas pelo `uv.lock`, em ambiente Python 3.12 separado do ambiente existente.
  Inclui autorização explícita, matriz de acesso, auditoria de contas/cenários,
  preservação de snapshots e concorrência do último QA.
- `frontend-tests.txt`: quatro casos do executor nativo do Node para fronteiras
  de datas locais, detalhes legados de auditoria, falhas de exportação e download
  autenticado com liberação de recursos temporários.
- `npm-audit.json`: diagnóstico do registro npm após atualizar Vite para 7.3.7.
- `verificacao.json`: contagens finais e identificação das imagens construídas.

As execuções preliminares foram mantidas fora da árvore versionada para não
confundir seus resultados com os testes finais. Os serviços de desenvolvimento
existentes não foram modificados. Não foram usados dados de produção, nem foi
realizado push, publicação de imagem ou criação de PR.
