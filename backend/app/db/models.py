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
