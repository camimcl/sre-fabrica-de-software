"""Explicit authorization cannot be obtained by coercing strings or numbers."""
import pytest
from test_sprint09_validation import api, context  # noqa: F401


@pytest.mark.parametrize('value', ['true', 'yes', '1', 1, 0, None])
@pytest.mark.parametrize('method', ['POST', 'PUT'])
def test_authorization_requires_a_json_boolean(context, value, method):
    client, headers, root, data, scenario = context
    path = root + '/endpoints'
    before = client.get(path, headers=headers).json()
    target = path if method == 'POST' else path + '/' + scenario['endpoint_id']
    response = client.request(method, target, headers=headers,
                              json={**data, 'authorization_confirmed': value})
    assert response.status_code == 422
    assert client.get(path, headers=headers).json() == before


@pytest.mark.parametrize('value', [False, True])
def test_real_booleans_keep_the_explicit_authorization_workflow(context, value):
    client, headers, root, data, _ = context
    response = client.post(root + '/endpoints', headers=headers,
                           json={**data, 'authorization_confirmed': value})
    assert response.status_code == 201
    assert response.json()['authorization_confirmed'] is value
