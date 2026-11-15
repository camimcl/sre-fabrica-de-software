"""RC smoke test against the isolated Compose lab; never targets a public host.

Requires lab.py up/bootstrap. Keeps all created demonstration data and writes
only sanitized evidence. Restarts/kills only the lab API, not normal services.
"""
import argparse
import csv
from datetime import datetime, timezone
import io
import json
import secrets
import subprocess
import time

import httpx

from lab import LOCAL, compose, credentials


def main(skip_restart=False):
    checks = []
    values = credentials()
    client = httpx.Client(base_url='http://127.0.0.1:58109', timeout=15)
    result = {'captured_at': datetime.now(timezone.utc).isoformat(), 'status': 'IN_PROGRESS',
              'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              'checks': checks}

    def save(status):
        result['status'] = status
        (LOCAL / 'rc-smoke.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    def checked(message):
        checks.append(message)
        save('IN_PROGRESS')

    def request(method, path, body=None, expected=200):
        response = client.request(method, path, json=body)
        assert response.status_code == expected, (method, path, response.status_code, response.text[:300])
        return response

    def login(email, password):
        client.headers.pop('Authorization', None)
        token = request('POST', '/auth/login', {'email': email, 'password': password}).json()['access_token']
        client.headers['Authorization'] = 'Bearer ' + token

    def wait_ready():
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                if client.get('/health/ready').status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(.3)
        raise AssertionError('Lab API did not recover within 60 seconds')

    def wait_execution(path, status):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            execution = request('GET', path).json()
            if execution['status'] == status:
                return execution
            assert execution['status'] in ('PENDING', 'RUNNING'), execution['status']
            time.sleep(.2)
        raise AssertionError(f'Execution did not reach {status}')

    login(values['qa_email'], values['qa_password'])
    assert request('GET', '/openapi.json').json()['info']['version'] == '1.0.0-rc.1'
    request('GET', '/docs')
    request('GET', '/redoc')
    checked('RC version, Swagger and ReDoc available over HTTP')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    project = request('POST', '/projects', {'name': 'RC - validação ' + stamp,
                      'description': 'Somente alvo Docker local autorizado; teste funcional, sem conclusão de ganho da IA.'}, 201).json()
    base = '/projects/' + project['id']
    endpoint = request('POST', base + '/endpoints', {'name': 'Alvo isolado RC',
        'base_url': 'http://target:8080', 'http_method': 'GET', 'authorization_confirmed': True,
        'authorization_evidence': 'Serviço target pertencente ao laboratório Docker desta equipe.'}, 201).json()
    payload = {'name': 'RC fixa', 'endpoint_id': endpoint['id'], 'duration_seconds': 2,
               'initial_concurrency': 1, 'max_concurrency': 2, 'ramp_up_per_window': 1,
               'timeout_ms': 1000, 'strategy': 'FIXED', 'p95_limit_ms': 500, 'error_rate_limit': '0.1'}
    executions = []
    paths = []
    scenarios = []
    for strategy, name in [('FIXED', 'Fixa'), ('RULES', 'Regras'), ('AI_HYBRID', 'IA híbrida')]:
        scenario = request('POST', base + '/scenarios', {**payload, 'name': 'RC ' + name, 'strategy': strategy}, 201).json()
        scenarios.append(scenario)
        scenario_path = base + '/scenarios/' + scenario['id']
        for _ in range(3):
            run = request('POST', scenario_path + '/executions', {'authorization_acknowledged': True}, 201).json()
            path = scenario_path + '/executions/' + run['id']
            request('POST', path + '/start')
            wait_execution(path, 'COMPLETED')
            assert request('GET', path + '/metric-windows').json()
            if strategy != 'FIXED':
                assert request('GET', path + '/control-decisions').json()
            request('POST', path + '/report', expected=201)
            executions.append(run['id'])
            paths.append(path)
    checked('Nine completed runs: three repetitions per strategy, metrics, decisions and reports')
    comparison = request('POST', base + '/reports/comparisons', {'name': 'RC - comparação funcional',
                         'execution_ids': executions}, 201).json()
    assert comparison['repetitions_per_strategy'] == 3
    assert isinstance(comparison['results']['warnings'], list)
    checked('Repeated comparison persisted with structured warnings')
    for route, media, signature in [
        (paths[0] + '/report.pdf', 'application/pdf', b'%PDF'),
        (base + '/reports/comparisons/' + comparison['id'] + '.pdf', 'application/pdf', b'%PDF'),
        (base + '/reports/comparisons/' + comparison['id'] + '.csv', 'text/csv', None),
    ]:
        response = request('GET', route)
        assert response.headers['content-type'].startswith(media)
        assert 'attachment' in response.headers['content-disposition']
        if signature:
            assert response.content.startswith(signature)
    filtered = request('GET', base + '/executions?search=RC%20Fixa&status=COMPLETED&strategy=FIXED').json()
    assert filtered['total'] == 3
    exported = request('GET', base + '/exports/executions.csv?search=RC%20Fixa&status=COMPLETED&strategy=FIXED')
    rows = list(csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff'))))
    assert len(rows) == 3
    assert request('GET', base + '/dashboard').json()['totals']['executions'] == 9
    request('GET', base + '/dashboard?date_from=2026-12-01T00:00:00Z&date_to=2026-01-01T00:00:00Z', expected=422)
    checked('Dashboard, search and combined filters agree with CSV; execution and comparison PDFs valid')
    viewer_password = secrets.token_urlsafe(24)
    viewer_email = 'rc-' + secrets.token_hex(6) + '@example.org'
    request('POST', '/auth/register', {'full_name': 'Visualizador RC', 'email': viewer_email,
                                     'password': viewer_password}, 201)
    login(viewer_email, viewer_password)
    request('GET', base + '/dashboard')
    request('GET', paths[0] + '/report.pdf')
    request('POST', base + '/scenarios', payload, 403)
    request('GET', '/audit/logs', expected=403)
    checked('Viewer can consult/export but cannot create a scenario or access audit')
    result.update(project=project, scenarios=scenarios, execution_ids=executions, comparison_id=comparison['id'])
    if skip_restart:
        result['not_run'] = ['graceful container restart', 'SIGKILL and startup recovery']
        save('PASS_FUNCTIONAL_ONLY')
        client.close()
        print(f'PASS: {len(checks)} functional RC checks. Container restart/recovery NOT RUN.')
        return
    login(values['qa_email'], values['qa_password'])
    scenario = request('POST', base + '/scenarios', {**payload, 'name': 'RC recuperação', 'duration_seconds': 60}, 201).json()
    scenario_path = base + '/scenarios/' + scenario['id']

    def start():
        run = request('POST', scenario_path + '/executions', {'authorization_acknowledged': True}, 201).json()
        path = scenario_path + '/executions/' + run['id']
        request('POST', path + '/start')
        deadline = time.monotonic() + 10
        while not request('GET', path + '/metric-windows').json():
            assert time.monotonic() < deadline
            time.sleep(.2)
        return path, run

    graceful_path, _ = start()
    compose('restart', 'api', check=True, capture_output=True)
    wait_ready()
    assert request('GET', graceful_path).json()['status'] == 'CANCELLED'
    checked('Graceful API restart drains traffic and persists CANCELLED')
    crash_path, crashed = start()
    before = request('GET', crash_path + '/metric-windows').json()
    compose('kill', '-s', 'SIGKILL', 'api', check=True, capture_output=True)
    compose('start', 'api', check=True, capture_output=True)
    wait_ready()
    recovered = request('GET', crash_path).json()
    assert recovered['status'] == 'FAILED' and recovered['ended_at']
    assert 'interrompido' in recovered['cancellation_reason']
    after = request('GET', crash_path + '/metric-windows').json()
    assert after[:len(before)] == before
    logs = request('GET', '/audit/logs?entity_type=execution&page_size=100').json()['items']
    assert any(row['entity_id'] == crashed['id'] and 'recovery' in json.dumps(row['summary']) for row in logs)
    time.sleep(2.5)
    assert request('GET', crash_path + '/metric-windows').json() == after
    assert request('GET', base + '/reports/comparisons').json()[0]['id'] == comparison['id']
    checked('SIGKILL recovery persists FAILED and audit; preserves metrics/comparison and does not replay traffic')
    result['recovered_execution_id'] = crashed['id']
    save('PASS')
    client.close()
    print(f'PASS: {len(checks)} integrated RC checks. Evidence: .qa-local/rc-smoke.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-restart', action='store_true', help='Only functional checks; explicitly mark restart/recovery as not run')
    main(parser.parse_args().skip_restart)
