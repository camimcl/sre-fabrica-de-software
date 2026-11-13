"""Public API catalogue and portable OpenAPI export for the Release Candidate."""
from fastapi.openapi.utils import get_openapi

CATALOG = {
    'live': 'Verificar disponibilidade do processo', 'ready': 'Verificar conexão com o banco',
    'register': 'Cadastrar conta Visualizador', 'login': 'Autenticar e emitir token',
    'me': 'Consultar perfil da sessão', 'list_users': 'Pesquisar usuários',
    'create_user': 'Criar conta como QA', 'update_user': 'Atualizar conta e perfil',
    'delete_user': 'Excluir conta respeitando dependências',
    'list_projects': 'Pesquisar projetos', 'create_project': 'Criar projeto próprio',
    'get_project': 'Consultar projeto', 'update_project': 'Atualizar projeto próprio',
    'delete_project': 'Excluir projeto sem dependências', 'list_endpoints': 'Listar endpoints do projeto',
    'create_endpoint': 'Cadastrar endpoint e autorização', 'get_endpoint': 'Consultar endpoint',
    'update_endpoint': 'Atualizar endpoint e autorização', 'delete_endpoint': 'Excluir endpoint sem cenários',
    'query_project_executions': 'Pesquisar execuções com filtros e paginação',
    'list_scenarios': 'Pesquisar cenários', 'create_scenario': 'Criar cenário autorizado',
    'get_scenario': 'Consultar cenário', 'update_scenario': 'Atualizar cenário preservando snapshots',
    'delete_scenario': 'Excluir cenário sem execuções', 'list_executions': 'Listar execuções do cenário',
    'create_execution': 'Criar execução com confirmação explícita', 'get_execution': 'Consultar execução',
    'list_metric_windows': 'Consultar métricas coletadas por janela', 'start_execution': 'Iniciar tráfego autorizado',
    'complete_execution': 'Concluir execução sem motor ativo', 'fail_execution': 'Marcar falha sem motor ativo',
    'cancel_execution': 'Solicitar parada emergencial', 'list_models': 'Listar versões de modelos locais',
    'train_model': 'Treinar versão candidata com dados persistidos', 'approve_model': 'Aprovar modelo elegível',
    'list_predictions': 'Consultar previsões por janela', 'list_decisions': 'Consultar decisões de controle',
    'execution_history': 'Consultar histórico com relatórios',
    'create_execution_report_endpoint': 'Gerar relatório de execução terminal',
    'get_execution_report_endpoint': 'Consultar relatório individual persistido',
    'create_comparison': 'Comparar estratégias em condições equivalentes',
    'list_comparisons': 'Listar comparações persistidas', 'get_comparison': 'Consultar comparação',
    'project_dashboard': 'Consultar indicadores reais do projeto', 'list_operation_logs': 'Consultar auditoria global',
    'export_executions_csv': 'Exportar consulta de execuções em CSV',
    'export_comparison_csv': 'Exportar comparação em CSV',
    'export_execution_report_pdf': 'Exportar relatório individual em PDF',
    'export_comparison_pdf': 'Exportar comparação em PDF',
}

DETAILS = {
    'register': 'Cadastro público cria somente VIEWER. Perfil extra é rejeitado; senha exige ao menos 12 caracteres.',
    'login': 'Envia e-mail e senha. Retorna access_token e expires_in; use Authorization: Bearer <token> nas demais chamadas. O perfil é consultado no banco em cada requisição.',
    'update_user': 'Própria conta ou QA. Somente QA muda perfis. Não é permitido remover o último QA nem despromover o proprietário de projetos.',
    'delete_user': 'Própria conta ou QA. O último QA e contas com dependências não podem ser excluídos.',
    'create_execution': 'QA proprietário. authorization_acknowledged deve ser booleano JSON true. Congela alvo e configurações; não inicia tráfego.',
    'start_execution': 'QA proprietário. Revalida autorização e snapshot. Transição PENDING → RUNNING; execução assíncrona. Consulte o estado e as métricas.',
    'cancel_execution': 'QA proprietário. Impede novas requisições; aguarda as em voo até resposta/timeout. Enquanto drena pode retornar RUNNING; consulte novamente até CANCELLED.',
    'create_comparison': 'QA proprietário. De 9 a 90 IDs únicos, três estratégias, pelo menos três repetições por estratégia, quantidades iguais e condições equivalentes. Todas concluídas. Falha aborta a transação. Fallback não comprova ganho da IA.',
    'create_execution_report_endpoint': 'QA proprietário. Exige execução terminal com métricas. O relatório é persistido e pode ser consultado/exportado por usuários autenticados.',
    'train_model': 'Somente QA. Exige amostras temporais suficientes e duas classes. Calibração/limiar usam validação; o teste é reservado. Retorna 409 se os dados forem insuficientes.',
    'approve_model': 'Somente QA. Confere artefato, hash, esquema e recall mínimo de 0,80. Uma única versão aprovada; a anterior é retirada. Não garante ganho de desempenho.',
    'list_operation_logs': 'Somente QA. Histórico global do ambiente, independente do projeto selecionado. Filtros por ator, ação, entidade e período; paginação limitada.',
    'project_dashboard': 'Autenticado. Período filtra execuções e indicadores de execuções concluídas. Cenários/endpoints/comparações são totais do projeto. Série diária em UTC; P95 médio é média dos P95 das janelas, não percentil global.',
    'complete_execution': 'QA proprietário. Retorna 409 se houver motor ativo; use cancel para interromper o tráfego.',
    'fail_execution': 'QA proprietário. Retorna 409 se houver motor ativo; use cancel para interromper o tráfego.',
}

EXAMPLES = {
    'LoginRequest': {'email': 'qa@example.org', 'password': '<senha-configurada-localmente>'},
    'RegisterRequest': {'full_name': 'Usuário de consulta', 'email': 'viewer@example.org', 'password': '<senha-de-pelo-menos-12-caracteres>'},
    'UserCreateRequest': {'full_name': 'Usuário de consulta', 'email': 'viewer@example.org', 'password': '<senha-de-pelo-menos-12-caracteres>', 'role': 'VIEWER'},
    'UserUpdateRequest': {'full_name': 'Usuário atualizado', 'email': 'viewer@example.org', 'role': 'VIEWER', 'password': None},
    'ProjectWrite': {'name': 'Aplicação de homologação', 'description': 'Projeto com alvo autorizado'},
    'EndpointWrite': {'name': 'Saúde', 'base_url': 'http://target:8080/health', 'http_method': 'GET', 'authorization_confirmed': True, 'authorization_evidence': 'Ambiente local sob controle da equipe'},
    'ExecutionCreateRequest': {'authorization_acknowledged': True},
    'ExecutionCancelRequest': {'cancellation_reason': 'Parada solicitada pelo responsável'},
    'ScenarioWrite': {'name': 'Carga inicial', 'endpoint_id': '00000000-0000-4000-8000-000000000001', 'duration_seconds': 10, 'initial_concurrency': 1, 'max_concurrency': 4, 'ramp_up_per_window': 1, 'timeout_ms': 1000, 'strategy': 'RULES', 'p95_limit_ms': 500, 'error_rate_limit': '0.05'},
    'ComparisonCreateRequest': {'name': 'Ensaio equivalente', 'execution_ids': [f'00000000-0000-4000-8000-{i:012d}' for i in range(1, 10)]},
}


def install_openapi(app):
    def public_schema():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes,
                             description='LoadForge: carga autorizada, inteligência local, relatórios e auditoria. Ambiente compartilhado; escritas de projeto exigem QA proprietário.')
        schema['servers'] = [{'url': '/', 'description': 'API atual (o frontend utiliza o proxy /api)'}]
        route_names = {(route.path, method.lower()): route.name for route in app.routes
                       if getattr(route, 'include_in_schema', False)
                       for method in getattr(route, 'methods', [])}
        for path, item in schema['paths'].items():
            for method, operation in item.items():
                name = route_names[(path, method)]
                operation['summary'] = CATALOG[name]
                protected = bool(operation.get('security'))
                detail = DETAILS.get(name)
                if not detail:
                    if method == 'get':
                        detail = 'Consulta autenticada no ambiente compartilhado.' if protected else 'Consulta pública de saúde do serviço.'
                    elif path.startswith('/intelligence') or path == '/users':
                        detail = 'Somente QA. Alteração persistida e validada pela API.'
                    else:
                        detail = 'QA proprietário. Valida escopo, campos e dependências; conflitos retornam 409.'
                operation['description'] = detail + ' Os parâmetros, limites e schemas abaixo integram o contrato desta operação.'
                if name.startswith('export_'):
                    media = 'application/pdf' if name.endswith('_pdf') else 'text/csv'
                    operation['description'] += ' Retorna arquivo para download com Content-Disposition; utiliza dados persistidos e exige relatório já gerado quando aplicável.'
                    operation['responses']['200'] = {
                        'description': 'Arquivo exportado com sucesso.',
                        'headers': {'Content-Disposition': {'schema': {'type': 'string'}, 'description': 'attachment e nome do arquivo'}},
                        'content': {media: {'schema': {'type': 'string', **({'format': 'binary'} if media == 'application/pdf' else {})}}},
                    }
                errors = {}
                if protected or name == 'login': errors['401'] = 'Credenciais ausentes, inválidas ou expiradas.'
                if protected: errors['403'] = 'Perfil ou propriedade sem permissão para a operação.'
                if any(p.get('in') == 'path' for p in operation.get('parameters', [])): errors['404'] = 'Recurso inexistente ou fora do contexto informado.'
                if method != 'get' and name != 'login': errors['409'] = 'Conflito de estado, dependência, duplicidade ou regra de negócio.'
                if name == 'ready': errors['503'] = 'Banco indisponível.'
                for status, description in errors.items():
                    operation['responses'].setdefault(status, {'description': description, 'content': {'application/json': {'schema': {'type': 'object', 'required': ['detail'], 'properties': {'detail': {'type': 'string'}}}}}})
        for name, example in EXAMPLES.items():
            schema['components']['schemas'][name]['examples'] = [example]
        app.openapi_schema = schema
        return schema
    app.openapi = public_schema
