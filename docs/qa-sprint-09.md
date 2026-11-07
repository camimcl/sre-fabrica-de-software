# Roteiro de execução e revisão - Sprint 09

## Preparação do laboratório

Use Python 3.11/3.12 e as dependências fixadas do backend (`uv sync --locked --extra dev --no-install-project`). Execute com esse ambiente os comandos abaixo na raiz. Docker Desktop deve estar em execução. Não remova volumes do ambiente normal.

```powershell
python scripts/qa/lab.py up
python scripts/qa/lab.py bootstrap
python scripts/qa/lab.py suite --label minha-regressao
```

O laboratório usa frontend http://127.0.0.1:5189, API 58109 e PostgreSQL 55439. Credenciais são geradas em `.qa-local/credentials.json`; leia localmente qa_email e qa_password. Não as copie para commits ou capturas. `lab.py stop` interrompe apenas este laboratório e conserva os dados. A suíte usa banco terminado em `_test` separado da demonstração.

## Percurso manual detalhado

1. Abra 5189 em janela privada. Tente entrar com uma conta inexistente; confira a mensagem de recusa e ausência de acesso.
2. Entre com o QA local. Confira Projetos, Execuções, Relatórios, Dashboard e Usuários no menu.
3. Em Novo projeto, tente salvar sem Nome. O navegador deve indicar obrigatoriedade.
4. Crie um projeto com nome único e descrição. Confira seleção automática e quantidade na lista.
5. Edite a descrição e salve. Recarregue, selecione o projeto e confirme que a alteração permanece.
6. Em Novo endpoint, preencha Nome e URL inválida. O navegador deve bloquear o envio.
7. Use `http://target:8080`, marque autorização e deixe evidência vazia. Confira bloqueio obrigatório.
8. Preencha evidência identificando o alvo Docker da equipe e salve. Confira autorização registrada.
9. Edite o nome do endpoint, salve e recarregue. Confirme o novo nome.
10. Abra Execuções. Configure cenário com duração 2 s, inicial 3 e máxima 2. O botão Salvar deve ficar desabilitado.
11. Ajuste inicial 1, máxima 2, ajuste 1, P95 500 ms, erro 0,1, timeout 1000 ms e estratégia Regras. Salve.
12. Edite o cenário, digite um rascunho e cancele. Reabra edição e confirme os valores persistidos originais.
13. Sem marcar confirmação, confira Criar e iniciar desabilitado. Marque e inicie.
14. Acompanhe RUNNING até COMPLETED. Confira janelas, throughput, P95, erros e decisão no monitor.
15. Em Relatórios, gere o relatório individual. Abra Dashboard > Consultas e baixe o PDF da execução. Abra o arquivo e confira conteúdo.
16. Volte a Execuções e crie outro cenário com duração 30 s. Inicie, aguarde RUNNING e use Parada emergencial.
17. Aguarde CANCELLED. Recarregue e confirme que a execução continua cancelada.
18. Tente excluir cenário com histórico; a API deve impedir e a interface deve explicar a dependência.
19. Tente excluir endpoint com cenário e projeto com dependências; confirme recusa sem perda de dados.
20. Em ambiente novo sem 20 amostras temporais e duas classes, use Treinar nova versão e confira a explicação de insuficiência. Não aprove modelo abaixo de recall 0,80.
21. Para comparação, crie cenários idênticos nos parâmetros e alvo, variando somente FIXED, RULES e AI_HYBRID. Execute cada um três vezes, aguardando conclusão antes da próxima execução.
22. Em Relatórios, selecione as nove execuções, dê nome à evidência e gere comparação. Confira três repetições por estratégia e condições equivalentes.
23. Confira o aviso de fallback se não houver modelo aprovado. Não interprete esse resultado como ganho exclusivo de IA.
24. Exporte comparação CSV e PDF; abra ambos e confira identificação e métricas.
25. Abra Dashboard e confira totais do projeto, estados e estratégias. Compare com histórico; uma execução cancelada deve aparecer no total.
26. Preencha De posterior a Até. Confira mensagem e ausência de dados antigos; em Consultas, Atualizar e Exportar CSV devem estar desabilitados.
27. Limpe filtros. Confira recuperação dos indicadores.
28. Em Consultas, pesquise o nome de cenário FIXED. Confira somente as três execuções correspondentes.
29. Exporte CSV e confira que os registros correspondem ao filtro. Teste paginação quando houver mais de dez registros.
30. Abra Operações. Expanda uma operação e confira ação, objeto e detalhes. Use próxima/anterior quando disponível.
31. Em Usuários, crie um Visualizador com e-mail único e senha de ao menos 12 caracteres.
32. Edite seu nome, salve e recarregue. Confira persistência. Crie outra conta descartável e exclua com confirmação.
33. Saia. Confirme retorno ao login. Entre como Visualizador e abra o projeto criado.
34. Confira ausência de formulários de escrita, criação de execução e treino. Dashboard e relatórios existentes devem continuar consultáveis; Operações não deve aparecer.
35. Em Usuários, o Visualizador pode editar o próprio perfil sem promover seu papel.
36. Entre como segundo QA que não seja proprietário. Consulte o projeto, sem editar seus endpoints/cenários ou iniciar carga nele.
37. Para confirmar negações pela API e não apenas pelos botões, execute a suíte e confira casos sprint08_permissions e NAV-11/12.
38. Para verificar exclusão válida, crie projeto descartável, endpoint e cenário sem execução. Exclua nesta ordem: cenário, endpoint, projeto. Confirme que deixam de aparecer.
39. Use o teste de resposta atrasada abaixo: deve conservar o rascunho de B sem mostrar endpoint de A. Ele cria somente dados próprios do laboratório.
40. Use o teste de período abaixo: deve rejeitar intervalo invertido durante resposta pendente, sem carregamento preso, e recuperar ao limpar.
41. Execute persistence.py após o percurso automatizado, que prepara o fixture esperado. Ele reinicia apenas a API e recupera os dados por novo login e conexão SQL independente.
42. Registre resultado, horário, ID e captura se houver divergência. Evite repetir carga antes de confirmar o término da anterior.

## Automação reproduzível

Playwright deve estar disponível no Node; `PLAYWRIGHT_MODULE` pode apontar para uma instalação local do pacote. Edge é o navegador padrão; `QA_BROWSER_CHANNEL` permite outro canal instalado. Não é necessário alterar o código para inserir credenciais.

```powershell
node scripts/qa/navigation.mjs
node scripts/qa/context-race.mjs
node scripts/qa/dashboard-race.mjs
python scripts/qa/persistence.py
```

O percurso cria dados novos por execução e conserva o histórico para demonstração. Resultados e capturas brutos ficam em `.qa-local/`. O teste de persistência lê demo-project.json, criado ao finalizar navigation.mjs. Frontend: `npm test` e `npm run build`. O banco de testes não é o banco da apresentação.
