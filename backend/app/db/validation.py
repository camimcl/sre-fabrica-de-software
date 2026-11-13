"""Read-only release validation of the migrated PostgreSQL schema."""
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Enum, inspect, text

from app.db import models  # noqa: F401
from app.db.base import Base

CHECKS = {
    'endpoints': {'ck_endpoint_http_method'},
    'model_versions': {f'ck_model_{name}' for name in ('precision', 'recall', 'f1', 'accuracy', 'sample_count')},
    'test_scenarios': {f'ck_scenario_{name}' for name in ('duration', 'concurrency', 'ramp_up', 'timeout', 'p95_limit', 'error_limit', 'operational_limits')},
    'test_executions': {f'ck_execution_{name}' for name in ('duration', 'concurrency', 'ramp_up', 'timeout', 'p95_limit', 'error_limit', 'operational_limits', 'dates')},
    'metric_windows': {f'ck_metric_{name}' for name in ('sequence', 'window_duration', 'counts', 'non_negative', 'error_rate')},
    'risk_predictions': {'ck_prediction_probability', 'ck_prediction_latency'},
    'control_decisions': {'ck_decision_concurrency'},
    'execution_reports': {'ck_report_counts', 'ck_report_metrics'},
    'comparison_reports': {'ck_comparison_repetitions'},
    'comparison_report_executions': {'ck_comparison_repetition_number'},
}


def validate_database(connection) -> dict:
    if connection.dialect.name != 'postgresql':
        raise ValueError('Release database validation requires PostgreSQL')
    context = MigrationContext.configure(connection, opts={'compare_type': True})
    backend = Path(__file__).resolve().parents[2]
    scripts = ScriptDirectory.from_config(Config(str(backend/'alembic.ini')))
    current = set(context.get_current_heads())
    expected = set(scripts.get_heads())
    issues = []
    if current != expected:
        issues.append('Migration revision does not match the application head')
    inspector = inspect(connection)
    actual_tables = set(inspector.get_table_names()) - {'alembic_version'}
    if actual_tables != set(Base.metadata.tables):
        issues.append('Application table set differs from ORM metadata')
    differences = compare_metadata(context, Base.metadata)
    issues.extend(str(item) for item in differences)
    for table, required in CHECKS.items():
        if table in actual_tables:
            present = {item['name'] for item in inspector.get_check_constraints(table)}
            issues.extend(f'Missing check constraint: {name}' for name in sorted(required-present))
    enums = {item['name']: item['labels'] for item in inspector.get_enums()}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, Enum) and enums.get(column.type.name) != column.type.enums:
                issues.append(f'Enum labels differ: {column.type.name}')
    unvalidated = connection.scalar(text(
        "SELECT count(*) FROM pg_constraint WHERE connamespace = current_schema()::regnamespace AND NOT convalidated"))
    if unvalidated:
        issues.append('Database has constraints that were not validated')
    return {'ok': not issues, 'migration_heads': sorted(current),
            'tables': len(actual_tables), 'check_constraints': sum(len(v) for v in CHECKS.values()),
            'issues': issues}
