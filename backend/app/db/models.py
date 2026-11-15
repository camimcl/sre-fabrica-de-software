"""Register every persisted model in SQLAlchemy metadata."""

from app.modules.audit.models import OperationLog
from app.modules.auth.models import User
from app.modules.control.models import ControlDecision
from app.modules.intelligence.models import ModelVersion, RiskPrediction
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.metrics.models import MetricWindow
from app.modules.projects.models import Endpoint, Project
from app.modules.reports.models import (
    ComparisonReport,
    ComparisonReportExecution,
    ExecutionReport,
)
from sqlalchemy import Index

# Query indexes already installed by migrations are also represented in ORM
# metadata, so Alembic does not propose removing them during future revisions.
Index('ix_projects_owner_id', Project.owner_id)
Index('ix_endpoints_project_id', Endpoint.project_id)
Index('ix_scenarios_project_id', TestScenario.project_id)
Index('ix_scenarios_endpoint_id', TestScenario.endpoint_id)
Index('ix_executions_scenario_created', TestExecution.scenario_id, TestExecution.created_at.desc())
Index('ix_metric_windows_execution_time', MetricWindow.execution_id, MetricWindow.window_started_at)
Index('ix_predictions_model_version', RiskPrediction.model_version_id)
Index('ix_model_versions_status', ModelVersion.status)


__all__ = [
    "ControlDecision",
    "ComparisonReport",
    "ComparisonReportExecution",
    "Endpoint",
    "OperationLog",
    "ExecutionReport",
    "MetricWindow",
    "ModelVersion",
    "Project",
    "RiskPrediction",
    "TestExecution",
    "TestScenario",
    "User",
]
