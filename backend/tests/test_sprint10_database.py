import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.db.validation import validate_database


@pytest.fixture
def database():
    url = os.getenv('LOADFORGE_TEST_DATABASE_URL')
    if not url:
        pytest.skip('LOADFORGE_TEST_DATABASE_URL is not set')
    assert (make_url(url).database or '').endswith('_test')
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            yield connection
    finally:
        engine.dispose()


@pytest.mark.integration
def test_final_migrated_schema_matches_application(database):
    result = validate_database(database)
    assert result['ok'], result['issues']
    assert result['tables'] == 13
    assert result['migration_heads'] == ['20261020_0007']


@pytest.mark.integration
@pytest.mark.parametrize('change', ['constraint', 'index', 'primary_key'])
def test_schema_validation_detects_drift_without_repairing_it(database, change):
    transaction = database.begin()
    try:
        if change == 'constraint':
            database.execute(text('ALTER TABLE test_executions DROP CONSTRAINT ck_execution_concurrency'))
        elif change == 'index':
            database.execute(text('DROP INDEX ix_executions_scenario_created'))
        else:
            database.execute(text('ALTER TABLE operation_logs DROP CONSTRAINT operation_logs_pkey'))
            assert not inspect(database).get_pk_constraint('operation_logs')['constrained_columns']
        result = validate_database(database)
        assert not result['ok']
        assert any('ck_execution_concurrency' in issue or 'ix_executions_scenario_created' in issue or 'Primary key differs: operation_logs' in issue
                   for issue in result['issues'])
    finally:
        transaction.rollback()
    assert validate_database(database)['ok']
