from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.query import validate_date_range
from app.db.session import get_db
from app.db.types import ControlStrategy, ExecutionStatus
from app.modules.auth.api import current_user
from app.modules.auth.models import User
from app.modules.dashboard.schemas import (
    DashboardPerformance,
    DashboardResponse,
    DashboardTotals,
    TimeseriesPoint,
)
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.metrics.models import MetricWindow
from app.modules.projects.access import require_project
from app.modules.projects.models import Endpoint
from app.modules.reports.models import ComparisonReport


router = APIRouter(prefix="/projects", tags=["dashboard"])


def _project_execution_filter(project_id: UUID):
    return (
        select(TestExecution.id)
        .join(TestScenario, TestScenario.id == TestExecution.scenario_id)
        .where(TestScenario.project_id == project_id)
    )


@router.get("/{project_id}/dashboard", response_model=DashboardResponse)
def project_dashboard(
    project_id: UUID,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    require_project(db, project_id)
    validate_date_range(date_from, date_to)

    base = (
        select(TestExecution)
        .join(TestScenario, TestScenario.id == TestExecution.scenario_id)
        .where(TestScenario.project_id == project_id)
    )
    if date_from is not None:
        base = base.where(TestExecution.created_at >= date_from)
    if date_to is not None:
        base = base.where(TestExecution.created_at <= date_to)
    executions = list(db.scalars(base))

    by_status: dict[str, int] = {status.value: 0 for status in ExecutionStatus}
    by_strategy: dict[str, int] = {strategy.value: 0 for strategy in ControlStrategy}
    per_day: dict[str, int] = {}
    for execution in executions:
        by_status[execution.status.value] += 1
        by_strategy[execution.strategy.value] += 1
        day = execution.created_at.date().isoformat()
        per_day[day] = per_day.get(day, 0) + 1

    total_executions = len(executions)
    completed = by_status[ExecutionStatus.COMPLETED.value]
    completion_rate = completed / total_executions if total_executions else 0.0

    scenarios = db.scalar(
        select(func.count())
        .select_from(TestScenario)
        .where(TestScenario.project_id == project_id)
    ) or 0
    endpoints = db.scalar(
        select(func.count())
        .select_from(Endpoint)
        .where(Endpoint.project_id == project_id)
    ) or 0
    comparisons = db.scalar(
        select(func.count())
        .select_from(ComparisonReport)
        .where(ComparisonReport.project_id == project_id)
    ) or 0

    # Performance averages over metric windows of this project's executions.
    completed_ids = [
        execution.id
        for execution in executions
        if execution.status == ExecutionStatus.COMPLETED
    ]
    avg_throughput = avg_p95 = avg_error = 0.0
    if completed_ids:
        row = db.execute(
            select(
                func.avg(MetricWindow.throughput_rps),
                func.avg(MetricWindow.latency_p95_ms),
                func.avg(MetricWindow.error_rate),
            ).where(MetricWindow.execution_id.in_(completed_ids))
        ).one()
        avg_throughput = float(row[0] or 0)
        avg_p95 = float(row[1] or 0)
        avg_error = float(row[2] or 0)

    timeseries = [
        TimeseriesPoint(day=day, count=count)
        for day, count in sorted(per_day.items())
    ]
    return DashboardResponse(
        totals=DashboardTotals(
            executions=total_executions,
            scenarios=scenarios,
            endpoints=endpoints,
            comparisons=comparisons,
        ),
        executions_by_status=by_status,
        executions_by_strategy=by_strategy,
        completion_rate=round(completion_rate, 5),
        performance=DashboardPerformance(
            avg_throughput_rps=round(avg_throughput, 4),
            avg_latency_p95_ms=round(avg_p95, 3),
            avg_error_rate=round(avg_error, 5),
        ),
        timeseries_executions_per_day=timeseries,
    )
