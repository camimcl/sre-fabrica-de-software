# Operação da Release Candidate 1.0.0-rc.1

Base da Sprint 09: `cc9984f`. Esta RC consolida o MVP sem retirar funcionalidades.
O backend usa a grafia PEP 440 `1.0.0rc1` no empacotamento; interface e OpenAPI
usam a grafia SemVer `1.0.0-rc.1`. São a mesma versão candidata.

## Instalação e primeiro acesso

Siga o [README](../README.md): configure os segredos no `.env`, execute
`docker compose up --build -d`, crie o primeiro QA pelo comando interativo e
verifique `docker compose ps` e `docker compose exec api python -m app.cli check-db`.
As migrations são aplicadas antes de a API iniciar. Não use `create_all` para
provisionar instalações ou atualizações: Alembic é a fonte do histórico do banco.

## Banco final

PostgreSQL 16, migration `20261020_0007`, 13 tabelas de aplicação:

| Área | Tabelas |
|---|---|
| Identidade e configuração | `users`, `projects`, `endpoints` |
| Carga e métricas | `test_scenarios`, `test_executions`, `metric_windows` |
| Inteligência e controle | `model_versions`, `risk_predictions`, `control_decisions` |
| Relatórios e comparação | `execution_reports`, `comparison_reports`, `comparison_report_executions` |
| Rastreabilidade | `operation_logs` |

`alembic_version` é a tabela de controle de migrations, além das 13 acima.
A RC não exige nova migration: os oito índices de consulta já existentes no
banco foram declarados também nos metadados ORM. Isso elimina diferenças falsas
em futuras comparações/autogerações sem duplicar índices nem reescrever históricos.

`check-db` confere revisão, tabelas, colunas, tipos, nulabilidade, chaves,
unicidade, índices, presença das 33 CHECKs esperadas, enums e restrições não
validadas. Não altera dados. Divergências retornam `ok: false` e código de saída
1; corrija a causa antes de entregar. A verificação de CHECKs comprova presença
e validação, não equivalência semântica de toda expressão SQL modificada manualmente.

## Ciclo de vida da API e do motor

Use **um único processo/worker de API por banco**, com
`LOADFORGE_MANAGED_RUNTIME=1` (forçado pelo Compose e recomendado fora dele).
Uma conexão dedicada mantém um advisory lock PostgreSQL durante a vida da API.
Outra API gerenciada no mesmo banco falha ao iniciar, antes de recuperar históricos.
Modo `0` existe para importação da biblioteca e clientes isolados de testes;
não use esse modo para servir tráfego real.

No encerramento normal, o motor sinaliza cancelamento e aguarda requisições em
voo até seu timeout. O runtime aguarda até 70 s e o Compose concede 75 s. Não
há envio de novas requisições depois de o cancelamento ser observado. Um
cancelamento forçado da tarefa registra falha e libera o registro em memória.

Na próxima inicialização após queda abrupta, execuções persistidas como RUNNING
são encerradas como FAILED, com data, motivo e operação de recuperação na
auditoria. Cenários, snapshots, métricas e relatórios existentes são preservados.
Não existe replay automático: o usuário decide se cria outra execução.

Se o PostgreSQL cair durante uma execução, interrompa o uso e reinicie a API
após a recuperação do banco. A posse exclusiva depende da conexão PostgreSQL;
não há eleição distribuída, failover transparente ou retomada de tráfego.
Não execute instâncias com runtime desabilitado paralelamente à API gerenciada.

## Atualização, cópia de segurança e retorno

Antes de atualizar uma instalação com dados relevantes:

1. Aguarde/paralise execuções pelo produto e interrompa a API com
   `docker compose stop api`. Preserve o `.env` fora do repositório.
2. Gere um dump PostgreSQL em formato customizado dentro do contêiner e copie-o
   para uma pasta protegida do computador, evitando redirecionamento binário no
   PowerShell. Substitua `loadforge` se alterou usuário/banco no `.env`:

   ```bash
   docker compose exec db pg_dump -U loadforge -d loadforge -Fc -f /tmp/loadforge.dump
   docker compose cp db:/tmp/loadforge.dump ./loadforge.dump
   ```

3. Copie também os artefatos. `docker compose cp api:/app/backend/models/artifacts ./model-artifacts-backup`
   funciona com o contêiner parado. Banco e arquivos devem pertencer ao mesmo
   ponto de parada; não carregue arquivos joblib de origem não confiável.
4. Atualize o código, reconstrua e inicie pelo README. Execute `check-db`, login,
   consulta de histórico e um teste autorizado pequeno antes de liberar uso.

Não versione dumps ou artefatos. Não execute `docker compose down -v` ao atualizar.
Para retorno desta RC à base da Sprint 09, pare a API e reconstrua a revisão
anterior: o esquema não mudou. Isso não reverte dados criados depois do backup.
Uma restauração deve ser ensaiada em **outro banco vazio**, por exemplo copiando
o dump para o contêiner e usando `pg_restore -U loadforge -d BANCO_VAZIO
--no-owner --no-privileges /tmp/loadforge.dump`. Configure a aplicação de
validação para esse banco e seus artefatos, aplique/verifique migrations e só
então planeje a substituição do ambiente. Não restaure sobre um banco em uso.
O ensaio completo de backup/restauração de produção depende da infraestrutura
da equipe e não é declarado executado nesta sprint.

## API e uso integrado

O [guia de API](api/README.md) apresenta autenticação Bearer, permissões,
exemplos e um fluxo de ponta a ponta; a [referência](api/referencia.md) relaciona
todas as operações. Swagger `/docs`, ReDoc `/redoc` e `/openapi.json` são
gerados pela API. As exportações documentam seus tipos reais CSV/PDF.

QA administra usuários e modelos e só altera projetos próprios. Visualizador
consulta projetos/resultados e gerencia a própria conta; não inicia testes,
aprova modelos ou lê a auditoria global. A autorização é validada no backend.

## Verificação reproduzível

Instale as dependências fixadas conforme o README. Testes de integração exigem
PostgreSQL descartável cujo nome termine em `_test`, migrations aplicadas e
`LOADFORGE_TEST_DATABASE_URL` configurado. Nunca use dados reais nos testes.

```bash
# Diretório backend, com DATABASE_URL apontando para o banco de teste:
uv run --no-sync alembic upgrade head
uv run --no-sync python -m app.cli check-db
uv run --no-sync pytest -q -p no:cacheprovider --junitxml=test-results/pytest.xml
uv run --no-sync python ../scripts/export_api_reference.py --check
# Diretório frontend:
npm ci
npm test
npm run build
```

O laboratório da Sprint 09 permanece compatível e separado dos serviços normais.
Na raiz, usando o Python com dependências do backend:

```bash
python scripts/qa/lab.py up
python scripts/qa/lab.py bootstrap
python scripts/qa/lab.py suite --label rc
python scripts/qa/release_candidate.py
python scripts/qa/lab.py stop
```

O roteiro RC cria somente alvos `http://target:8080` do laboratório, conserva os
dados de demonstração, verifica três repetições por estratégia, relatórios,
CSV/PDF, filtros, permissões e recuperação. **Reinicia e mata apenas a API do
laboratório** durante o teste; não use o laboratório para outra demonstração
simultânea. Resultados e credenciais ficam separados em `.qa-local`; não
publique credenciais. Confira também o [roteiro manual](qa-sprint-09.md).

Para verificar somente os fluxos HTTP sem interromper o contêiner, use
`python scripts/qa/release_candidate.py --skip-restart`. Nesse modo, o resultado
declara `PASS_FUNCTIONAL_ONLY` e lista reinício/recuperação como não executados;
isso não substitui o aceite completo. Cada etapa concluída é salva antes da
próxima; `IN_PROGRESS` não significa aprovação do roteiro inteiro.

## Limites para a entrega final

- Os testes locais não substituem homologação com usuários e infraestrutura de entrega.
- A comparação curta do laboratório comprova integração. Sem modelo aprovado,
  IA híbrida usa fallback; não demonstra ganho exclusivo da inferência.
- Recall mínimo de 0,80 continua requisito para aprovar novos modelos. Os
  resultados históricos inferiores não foram apagados.
- CPU do alvo não é medida; o campo de CPU local conserva o fallback documentado
  do motor. Não use esses dados para afirmar consumo real de CPU do alvo.
- Carga distribuída, alta disponibilidade, execução em múltiplos workers,
  deploy público e expansão do escopo continuam fora desta RC.
- Identificação e papéis da equipe vieram do README existente; matrículas,
  assinaturas e aceite da banca não foram inventados.
