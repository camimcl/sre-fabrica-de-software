"""Exercise historical rows through Alembic in a disposable PostgreSQL schema."""
import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.engine import make_url


@pytest.mark.integration
@pytest.mark.parametrize('oversized', ['test_scenarios', 'test_executions', None])
def test_sprint05_migration_preserves_history_and_reports_conflicts(monkeypatch, oversized):
    configured = os.getenv('LOADFORGE_TEST_DATABASE_URL')
    if not configured:
        pytest.skip('LOADFORGE_TEST_DATABASE_URL is not set')
    url = make_url(configured)
    if not (url.database or '').endswith('_test'):
        pytest.fail('Migration tests require a database ending in _test')
    schema = 'sprint05_' + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    isolated_url = url.update_query_dict({'options': f'-csearch_path={schema}'})
    monkeypatch.setenv('DATABASE_URL', isolated_url.render_as_string(hide_password=False))
    database = create_engine(isolated_url)
    try:
        command.upgrade(Config('alembic.ini'), '20260925_0002')
        metadata = MetaData()
        tables = {name: Table(name, metadata, autoload_with=database) for name in (
            'users', 'projects', 'endpoints', 'test_scenarios', 'test_executions',
        )}
        user, project, endpoint, scenario, execution = [uuid4() for _ in range(5)]
        with database.begin() as connection:
            connection.execute(tables['users'].insert().values(id=user,full_name='QA',email='qa@example.org',password_hash='fixture',role='QA'))
            connection.execute(tables['projects'].insert().values(id=project,owner_id=user,name='History'))
            connection.execute(tables['endpoints'].insert().values(id=endpoint,project_id=project,name='Target',base_url='http://127.0.0.1',http_method='GET'))
            common = dict(strategy='RULES',duration_seconds=60,initial_concurrency=2,max_concurrency=4,timeout_ms=1000,p95_limit_ms=500,error_rate_limit='0.1')
            scenario_values = dict(common, id=scenario,project_id=project,endpoint_id=endpoint,created_by=user,name='Historical',ramp_up_per_window=2)
            execution_values = dict(common, id=execution,scenario_id=scenario,initiated_by=user,status='COMPLETED',authorization_acknowledged=True)
            if oversized == 'test_scenarios':
                scenario_values['max_concurrency'] = 600
            if oversized == 'test_executions':
                execution_values['max_concurrency'] = 600
            connection.execute(tables['test_scenarios'].insert().values(**scenario_values))
            connection.execute(tables['test_executions'].insert().values(**execution_values))
            before = connection.execute(select(tables['test_executions'])).mappings().one()
        if oversized:
            with pytest.raises(Exception, match='Sprint 05 preflight'):
                command.upgrade(Config('alembic.ini'), 'head')
            assert 'ramp_up_per_window' not in {c['name'] for c in inspect(database).get_columns('test_executions')}
            with database.connect() as connection:
                assert connection.execute(select(tables['test_executions'])).mappings().one() == before
                assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '20260925_0002'
                assert connection.scalar(text(f'SELECT max_concurrency FROM {oversized}')) == 600
        else:
            command.upgrade(Config('alembic.ini'), 'head')
            with database.connect() as connection:
                assert connection.execute(select(tables['test_executions'])).mappings().one() == before
                assert connection.scalar(text('SELECT ramp_up_per_window FROM test_executions')) == 2
                assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '20261001_0004'
    finally:
        database.dispose()
        # Only the unique schema created above in the explicitly disposable test DB.
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
