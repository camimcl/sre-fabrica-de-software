import json
from pathlib import Path

import pytest
from app.main import app
from app.modules.auth import schemas as auth
from app.modules.projects import schemas as projects
from app.modules.load_tests import schemas as executions
from app.modules.reports import schemas as reports


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
