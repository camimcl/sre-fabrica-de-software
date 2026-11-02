"""Exercise the shared-environment permission contract through real HTTP routes."""

import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from test_api import api, _qa, _token  # noqa: F401 - shared isolated API fixture
from app.modules.audit.models import OperationLog
from app.db.types import AuditAction
from app.modules.load_tests import api as load_api
from app.modules.load_tests.models import TestExecution


@pytest.fixture
def resources(api, monkeypatch):
    client, factory = api
    monkeypatch.setattr(load_api, "ENGINE_ENABLED", False)
    owner = _qa(factory)
    other = _qa(factory, "other-qa@example.org")
    owner_headers = _token(client, owner.email, "strong-password-123")
    other_headers = _token(client, other.email, "strong-password-123")
    viewer = {"full_name": "Read Only", "email": "viewer@example.org", "password": "viewer-password-123"}
    viewer_id = client.post('/auth/register', json=viewer).json()['id']
    viewer_headers = _token(client, viewer['email'], viewer['password'])
    project = client.post('/projects', headers=owner_headers, json={'name': 'Sprint 08'}).json()['id']
    endpoint_data = {'name': 'Authorized', 'base_url': 'https://example.org/work', 'http_method': 'GET',
                     'authorization_confirmed': True, 'authorization_evidence': 'Owner authorization'}
    endpoint = client.post(f'/projects/{project}/endpoints', headers=owner_headers, json=endpoint_data).json()['id']
    scenario_data = {'name': 'Baseline', 'endpoint_id': endpoint, 'duration_seconds': 4,
                     'initial_concurrency': 1, 'max_concurrency': 3, 'ramp_up_per_window': 1,
                     'timeout_ms': 1000, 'strategy': 'FIXED', 'p95_limit_ms': 500, 'error_rate_limit': '0.05'}
    scenario = client.post(f'/projects/{project}/scenarios', headers=owner_headers, json=scenario_data).json()['id']
    base = f'/projects/{project}/scenarios/{scenario}'
    execution = client.post(f'{base}/executions', headers=owner_headers,
                            json={'authorization_acknowledged': True}).json()['id']
    return locals()


@pytest.mark.parametrize('actor', ['viewer_headers', 'other_headers'])
def test_project_mutations_require_both_role_and_ownership(resources, actor):
    r = resources; client = r['client']; headers = r[actor]
    root = f"/projects/{r['project']}"; scenario = r['base']; execution = f"{scenario}/executions/{r['execution']}"
    operations = [
        ('PUT', root, {'name': 'Forbidden'}), ('DELETE', root, None),
        ('POST', f'{root}/endpoints', r['endpoint_data']),
        ('PUT', f"{root}/endpoints/{r['endpoint']}", r['endpoint_data']),
        ('DELETE', f"{root}/endpoints/{r['endpoint']}", None),
        ('POST', f'{root}/scenarios', r['scenario_data']),
        ('PUT', scenario, r['scenario_data']), ('DELETE', scenario, None),
        ('POST', f'{scenario}/executions', {'authorization_acknowledged': True}),
        ('POST', f'{execution}/start', None), ('POST', f'{execution}/complete', None),
        ('POST', f'{execution}/fail', None),
        ('POST', f'{execution}/cancel', {'cancellation_reason': 'Denied'}),
        ('POST', f'{execution}/report', None),
        ('POST', f'{root}/reports/comparisons', {'name': 'Denied', 'execution_ids': [str(uuid4()) for _ in range(9)]}),
    ]
    for method, path, payload in operations:
        response = client.request(method, path, headers=headers, json=payload)
        assert response.status_code == 403, (method, path, response.text)
    assert client.get(execution, headers=r['owner_headers']).json()['status'] == 'PENDING'


def test_viewer_reads_shared_results_but_cannot_administer(resources):
    r = resources; client = r['client']; h = r['viewer_headers']; root = f"/projects/{r['project']}"
    for path in ['/projects', root, f'{root}/endpoints', f'{root}/scenarios', f'{root}/executions',
                 f'{root}/dashboard', f'{root}/reports/executions', f'{root}/reports/comparisons',
                 f'{root}/exports/executions.csv', '/intelligence/models', '/auth/me']:
        assert client.get(path, headers=h).status_code == 200, path
        assert client.get(path).status_code == 401, path
    for path in ['/users', '/audit/logs']:
        assert client.get(path, headers=h).status_code == 403
        assert client.get(path, headers=r['owner_headers']).status_code == 200
    assert client.post('/intelligence/models/train', headers=h).status_code == 403
    assert client.post('/projects', headers=h, json={'name': 'Blocked'}).status_code == 403


def test_role_changes_apply_to_existing_sessions_and_are_audited(resources):
    r = resources; client = r['client']
    payload = {**r['viewer'], 'role': 'QA', 'password': None}
    response = client.put(f"/users/{r['viewer_id']}", headers=r['owner_headers'], json=payload)
    assert response.status_code == 200, response.text
    assert client.get('/users', headers=r['viewer_headers']).status_code == 200
    payload['role'] = 'VIEWER'
    assert client.put(f"/users/{r['viewer_id']}", headers=r['owner_headers'], json=payload).status_code == 200
    assert client.get('/users', headers=r['viewer_headers']).status_code == 403
    assert client.put(f"/users/{r['viewer_id']}", headers=r['viewer_headers'],
                      json={**payload, 'role': 'QA'}).status_code == 403
    with r['factory']() as db:
        logs = list(db.scalars(select(OperationLog).where(OperationLog.entity_type == 'user', OperationLog.action == AuditAction.UPDATE)))
        assert len(logs) == 2
        assert json.loads(logs[-1].summary)['changed']['role']['after'] == 'VIEWER'
        assert all('password_hash' not in entry.summary and 'access_token' not in entry.summary
                   and r['viewer']['password'] not in entry.summary for entry in logs)


def test_scenario_edit_preserves_execution_snapshot_and_records_history(resources):
    r = resources; client = r['client']; headers = r['owner_headers']
    execution_path = f"{r['base']}/executions/{r['execution']}"
    before = client.get(execution_path, headers=headers).json()
    with r['factory']() as db:
        target_snapshot = db.get(TestExecution, UUID(r['execution'])).target_snapshot
    response = client.put(r['base'], headers=headers, json={**r['scenario_data'], 'timeout_ms': 2500, 'name': 'Edited'})
    assert response.status_code == 200, response.text
    after = client.get(execution_path, headers=headers).json()
    assert before['timeout_ms'] == after['timeout_ms'] == 1000
    with r['factory']() as db:
        assert db.get(TestExecution, UUID(r['execution'])).target_snapshot == target_snapshot
    # A fresh scenario without history can be deleted; its audit survives deletion.
    created = client.post(f"/projects/{r['project']}/scenarios", headers=headers, json=r['scenario_data']).json()['id']
    assert client.delete(f"/projects/{r['project']}/scenarios/{created}", headers=headers).status_code == 204
    with r['factory']() as db:
        logs = list(db.scalars(select(OperationLog).where(OperationLog.entity_type == 'scenario')))
        assert {entry.action.value for entry in logs} == {'CREATE', 'UPDATE', 'DELETE'}


@pytest.mark.parametrize('payload', [{}, {'authorization_acknowledged': False},
                                    {'authorization_acknowledged': 'true'},
                                    {'authorization_acknowledged': 1}])
def test_execution_requires_explicit_boolean_authorization(resources, payload):
    r = resources
    before = r['client'].get(f"{r['base']}/executions", headers=r['owner_headers']).json()
    response = r['client'].post(f"{r['base']}/executions", headers=r['owner_headers'], json=payload)
    assert response.status_code == 422, response.text
    assert r['client'].get(f"{r['base']}/executions", headers=r['owner_headers']).json() == before
