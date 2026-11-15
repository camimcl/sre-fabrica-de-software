import json
from pathlib import Path

import pytest
from app.main import app
from app.modules.auth import schemas as auth
from app.modules.projects import schemas as projects
from app.modules.load_tests import schemas as executions
from app.modules.reports import schemas as reports
from test_api import api  # noqa: F401
from test_sprint08_permissions import resources  # noqa: F401


@pytest.mark.parametrize('suffix', ['/executions', '/dashboard', '/exports/executions.csv', 'audit'])
@pytest.mark.parametrize('query,detail_type', [
    ('date_from=2026-12-01T00:00:00Z&date_to=2026-01-01T00:00:00Z', str),
    ('date_from=invalid', list),
])
def test_period_error_contract_matches_real_http_response(resources, suffix, query, detail_type):
    r = resources
    route = '/audit/logs' if suffix == 'audit' else f"/projects/{r['project']}" + suffix
    response = r['client'].get(route + '?' + query, headers=r['owner_headers'])
    assert response.status_code == 422
    assert isinstance(response.json()['detail'], detail_type)
    path = '/audit/logs' if suffix == 'audit' else '/projects/{project_id}' + suffix
    choices = app.openapi()['paths'][path]['get']['responses']['422']['content']['application/json']['schema']['anyOf']
    assert choices[0] == {'$ref': '#/components/schemas/HTTPValidationError'}
    assert app.openapi()['components']['schemas']['HTTPValidationError']['properties']['detail']['type'] == 'array'
    assert choices[1]['required'] == ['detail']
    assert choices[1]['properties']['detail']['type'] == 'string'


def test_user_list_requires_qa_in_contract_and_http(resources):
    r = resources
    assert 'Somente QA' in app.openapi()['paths']['/users']['get']['description']
    assert r['client'].get('/users', headers=r['viewer_headers']).status_code == 403
    assert r['client'].get('/users', headers=r['owner_headers']).status_code == 200


def operations():
    return [(path, method, operation) for path, item in app.openapi()['paths'].items()
            for method, operation in item.items()]


def test_public_contract_documents_authentication_and_error_responses():
    public = {'/auth/login', '/auth/register', '/health/live', '/health/ready'}
    for path, method, operation in operations():
        assert operation['summary'] and operation['description']
        if path in public:
            assert not operation.get('security')
        else:
            assert operation['security']
            assert '401' in operation['responses']
    assert app.openapi()['components']['securitySchemes']['HTTPBearer']['scheme'] == 'bearer'


def test_export_contract_uses_actual_download_media_types():
    for path, _, operation in operations():
        if path.endswith(('.csv', '.pdf')):
            media = 'text/csv' if path.endswith('.csv') else 'application/pdf'
            response = operation['responses']['200']
            assert set(response['content']) == {media}
            assert 'Content-Disposition' in response['headers']


@pytest.mark.parametrize('model', [auth.LoginRequest, auth.RegisterRequest, auth.UserCreateRequest,
    auth.UserUpdateRequest, projects.ProjectWrite, projects.EndpointWrite,
    executions.ExecutionCreateRequest, executions.ExecutionCancelRequest,
    executions.ScenarioWrite, reports.ComparisonCreateRequest])
def test_documented_request_examples_match_real_validation(model):
    example = app.openapi()['components']['schemas'][model.__name__]['examples'][0]
    assert model.model_validate(example)


def test_committed_contract_matches_application_routes():
    document = Path(__file__).resolve().parents[2]/'docs/api/openapi.json'
    assert json.loads(document.read_text(encoding='utf-8')) == app.openapi()
