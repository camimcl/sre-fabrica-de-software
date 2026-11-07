"""S09 validation matrix through HTTP; rejected input must not mutate data."""
import pytest

from test_api import api, _qa, _token  # noqa: F401


@pytest.fixture
def context(api):
    client, factory = api
    # SQLite disables foreign keys by default; enforce the relational contract.
    with factory.kw['bind'].connect() as connection:
        connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    actor = _qa(factory)
    headers = _token(client, actor.email, 'strong-password-123')
    project = client.post('/projects', headers=headers, json={'name': 'S09 validations'}).json()['id']
    root = f'/projects/{project}'
    endpoint_data = {'name': 'Local target', 'base_url': 'http://127.0.0.1:8080',
                     'authorization_confirmed': True, 'authorization_evidence': 'Local QA target'}
    endpoint = client.post(root + '/endpoints', headers=headers, json=endpoint_data).json()['id']
    scenario = {'name': 'S09', 'endpoint_id': endpoint, 'duration_seconds': 2,
                'initial_concurrency': 1, 'max_concurrency': 2, 'ramp_up_per_window': 1,
                'timeout_ms': 500, 'strategy': 'RULES', 'p95_limit_ms': 200,
                'error_rate_limit': '0.1'}
    return client, headers, root, endpoint_data, scenario


@pytest.mark.parametrize('field,value', [
    ('name', ''), ('name', '   '), ('name', 'x' * 121),
    ('duration_seconds', 0), ('duration_seconds', 3601),
    ('initial_concurrency', 0), ('initial_concurrency', 3),
    ('max_concurrency', 501), ('ramp_up_per_window', -1),
    ('timeout_ms', 0), ('timeout_ms', 60001), ('p95_limit_ms', 0),
    ('error_rate_limit', '-0.1'), ('error_rate_limit', '1.1'),
    ('strategy', 'UNKNOWN'), ('endpoint_id', 'invalid-uuid'),
])
def test_s09_invalid_scenario_is_explained_and_not_persisted(context, field, value):
    client, headers, root, _, scenario = context
    path = root + '/scenarios'
    before = client.get(path, headers=headers).json()
    rejected = client.post(path, headers=headers, json={**scenario, field: value})
    assert rejected.status_code == 422
    assert rejected.json()['detail'][0]['msg']
    assert client.get(path, headers=headers).json() == before


@pytest.mark.parametrize('patch', [
    {'base_url': 'ftp://127.0.0.1'}, {'base_url': 'not-a-url'},
    {'base_url': 'http://user:secret@localhost'}, {'base_url': 'http://localhost/#frag'},
    {'http_method': 'TRACE'}, {'authorization_evidence': '   '}, {'name': '   '},
])
def test_s09_endpoint_validation_preserves_existing_target(context, patch):
    client, headers, root, data, scenario = context
    path = root + '/endpoints/' + scenario['endpoint_id']
    before = client.get(path, headers=headers).json()
    result = client.put(path, headers=headers, json={**data, **patch})
    assert result.status_code == 422
    assert result.json()['detail']
    assert client.get(path, headers=headers).json() == before


@pytest.mark.parametrize('field,value', [
    ('full_name', ' '), ('email', 'invalid'), ('password', 'short'), ('role', 'QA'),
])
def test_s09_invalid_public_registration_creates_no_account(api, field, value):
    client, factory = api
    actor = _qa(factory)
    headers = _token(client, actor.email, 'strong-password-123')
    before = client.get('/users', headers=headers).json()
    payload = {'full_name': 'Public viewer', 'email': 'new@example.org', 'password': 'test-only-password'}
    result = client.post('/auth/register', json={**payload, field: value})
    assert result.status_code == 422
    assert client.get('/users', headers=headers).json() == before


def test_s09_crud_chain_and_delete_dependencies(context):
    client, headers, root, _, scenario = context
    created = client.post(root + '/scenarios', headers=headers, json=scenario)
    assert created.status_code == 201
    path = root + '/scenarios/' + created.json()['id']
    assert client.put(path, headers=headers, json={**scenario, 'name': 'Reviewed', 'timeout_ms': 700}).status_code == 200
    assert client.get(path, headers=headers).json()['timeout_ms'] == 700
    endpoint_path = root + '/endpoints/' + scenario['endpoint_id']
    assert client.delete(endpoint_path, headers=headers).status_code == 409
    assert client.delete(root, headers=headers).status_code == 409
    assert client.delete(path, headers=headers).status_code == 204
    assert client.get(path, headers=headers).status_code == 404
    assert client.delete(endpoint_path, headers=headers).status_code == 204
    assert client.delete(root, headers=headers).status_code == 204
    assert client.get(root, headers=headers).status_code == 404
