"""Verify stored demonstration data through a new API process and DB connection."""
import json
from datetime import datetime, timezone
import time
import httpx
from sqlalchemy import create_engine, text
from lab import LOCAL, compose, credentials, database_url

demo = json.loads((LOCAL / 'demo-project.json').read_text())
project_id = demo['project']['id']
engine = create_engine(database_url('loadforge_s09_demo'))
with engine.connect() as db:
    tables = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
    counts = {}
    for table in ['test_scenarios', 'test_executions', 'metric_windows', 'execution_reports', 'comparison_reports']:
        counts[table] = db.execute(text(f'SELECT count(*) FROM {table}')).scalar_one()
    revision = db.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
engine.dispose()
compose('restart', 'api', check=True, capture_output=True)
with httpx.Client(base_url='http://127.0.0.1:58109') as client:
    for attempt in range(90):
        try:
            if client.get('/health/ready').status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    else:
        raise RuntimeError('API did not restart')
    values = credentials()
    login = client.post('/auth/login', json={'email': values['qa_email'], 'password': values['qa_password']})
    login.raise_for_status()
    headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
    project = client.get('/projects/' + project_id, headers=headers)
    dashboard = client.get(f'/projects/{project_id}/dashboard', headers=headers)
    comparisons = client.get(f'/projects/{project_id}/reports/comparisons', headers=headers)
    assert project.status_code == dashboard.status_code == comparisons.status_code == 200
    assert dashboard.json()['totals']['executions'] == 11
    assert len(comparisons.json()) == 1
result = {'captured_at': datetime.now(timezone.utc).isoformat(), 'status': 'PASS',
          'procedure': 'SQL counts using independent connection; API restart; fresh login and HTTP reads',
          'tables': tables, 'migration_head': revision, 'global_demo_counts': counts,
          'project_id': project_id, 'project_name_recovered': project.json()['name'],
          'dashboard_after_restart': dashboard.json(), 'comparisons_recovered': len(comparisons.json())}
(LOCAL / 'persistence.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('PASS: 11 project executions and one comparison recovered after API restart.')
