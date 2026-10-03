# Integração contínua

O workflow [LoadForge CI](../.github/workflows/ci.yml) verifica alterações antes da integração. É executado em PRs destinados à `main`, em pushes para `main` e manualmente pela aba Actions depois que o arquivo estiver na branch padrão. Novas atualizações do mesmo PR cancelam uma execução anterior ainda em andamento.

## Verificações

| Check | O que verifica | Resultado esperado |
|---|---|---|
| Backend + PostgreSQL | Python 3.11, instalação pelo `uv.lock`, todas as migrations e toda a suíte pytest, incluindo integração com PostgreSQL 16. | Nenhuma falha e nenhum teste ignorado; relatório XML disponível por 14 dias. |
| Frontend build | Node.js 22, instalação pelo `package-lock.json`, TypeScript e build Vite. | Compilação concluída sem erro. |
| Docker builds | Construção dos Dockerfiles da API e do frontend. | Ambas as imagens construídas, sem publicação em registry. |

O relatório de testes não tem uma quantidade fixa exigida: aceita a evolução da suíte, mas rejeita uma execução vazia ou com testes ignorados. Assim, a ausência de configuração do PostgreSQL não aparece como sucesso parcial. As imagens são apenas construídas; este check não substitui testes de inicialização do Compose ou navegação completa.

## Segurança e isolamento

- São usados runners Linux hospedados pelo GitHub e um PostgreSQL descartável, sem volumes persistentes ou acesso ao banco da equipe.
- A credencial `ci-disposable-only` é pública e exclusiva do serviço temporário de teste, exposto somente no loopback do runner. Não é uma senha da aplicação, do laboratório local ou de produção e não deve ser reutilizada. Nenhum secret do repositório é necessário para este workflow.
- O token automático recebe apenas `contents: read`; o checkout não mantém credenciais no Git. Não são usados `pull_request_target`, runners próprios, deploy, publicação de imagens ou merge automático.
- As actions estão fixadas por SHA completo. Atualizações devem conferir a origem e o novo SHA. Python, Node e PostgreSQL seguem as versões principais do projeto; as imagens-base ainda usam tags e exigem manutenção periódica.
- Somente o XML de testes é publicado como artifact. `.env`, modelos, credenciais e bancos não são anexados. Logs e artifacts de um repositório público devem ser tratados como públicos; fixtures nunca devem conter dados reais.

## Como acompanhar

1. Abra o PR e consulte a área de checks ou a aba **Actions** do repositório.
2. Abra a execução **LoadForge CI** e o job com falha. O primeiro passo vermelho normalmente identifica instalação, migration, teste ou compilação.
3. Para falhas do backend, consulte o log de pytest e o artifact `backend-test-results`, quando disponível. Se a instalação falhar antes dos testes, o XML não será gerado e o job continuará sinalizando falha.
4. Faça a correção em uma branch e publique o commit no PR para disparar uma nova verificação.
5. Depois que o workflow estiver na `main`, **Run workflow** permite uma execução manual. PRs de forks podem depender da aprovação de um mantenedor, conforme as configurações do GitHub.

Uma execução verde não aprova nem faz merge do PR. Para impedir a integração quando um check falhar, é necessário configurar separadamente um ruleset/proteção da `main`, exigindo os três checks acima e, se desejado, revisão humana. O workflow não altera essas regras por conta própria.

## Limites e evolução

O teste de navegador atual usa um laboratório previamente populado, IDs de execuções/modelos e credenciais locais. Ele permanece uma verificação local: ainda não há preparação automática desses dados nem coleta de 480 segundos neste workflow. Não são executadas cargas contra serviços externos. A compilação do frontend não equivale a um teste de navegação.

Auditoria periódica de dependências, análise estática de segurança e testes de ponta a ponta independentes do laboratório são evoluções separadas. CI reduz regressões cobertas pela suíte, mas não garante ausência de bugs ou vulnerabilidades.

## Referências

- [Serviços PostgreSQL no GitHub Actions](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).
- [Segurança de workflows](https://docs.github.com/en/actions/reference/security/secure-use).
- [uv no GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/).
