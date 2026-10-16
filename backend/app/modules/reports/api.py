import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.api import current_user, qa_user
from app.modules.auth.models import User
from app.modules.load_tests.api import _execution, _owned_project, _project, _scenario
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.reports.models import (
    ComparisonReport,
    ComparisonReportExecution,
    ExecutionReport,
)
from app.modules.reports.schemas import (
    ComparisonCreateRequest,
    ComparisonReportResponse,
    ExecutionHistoryItem,
    ExecutionReportResponse,
)
from app.modules.reports.service import (
    create_comparison_report,
    generate_execution_report,
)


router = APIRouter(prefix="/projects", tags=["reports"])


def _comparison_response(
    db: Session, comparison: ComparisonReport
) -> ComparisonReportResponse:
    execution_ids = list(
        db.scalars(
            select(ComparisonReportExecution.execution_id)
            .where(ComparisonReportExecution.comparison_report_id == comparison.id)
            .order_by(
                ComparisonReportExecution.strategy,
                ComparisonReportExecution.repetition_number,
            )
        )
    )
    return ComparisonReportResponse(
        id=comparison.id,
        project_id=comparison.project_id,
        created_by=comparison.created_by,
        name=comparison.name,
        repetitions_per_strategy=comparison.repetitions_per_strategy,
        conditions_fingerprint=comparison.conditions_fingerprint,
        conditions=json.loads(comparison.conditions_json),
        results=json.loads(comparison.results_json),
        conclusion=comparison.conclusion,
        execution_ids=execution_ids,
        generated_at=comparison.generated_at,
    )


@router.get("/{project_id}/reports/executions", response_model=list[ExecutionHistoryItem])
def execution_history(
    project_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[ExecutionHistoryItem]:
    _project(db, project_id)
    rows = db.execute(
        select(TestExecution, TestScenario, ExecutionReport)
        .join(TestScenario, TestScenario.id == TestExecution.scenario_id)
        .outerjoin(ExecutionReport, ExecutionReport.execution_id == TestExecution.id)
        .where(TestScenario.project_id == project_id)
        .order_by(TestExecution.created_at.desc())
    ).all()
    return [
        ExecutionHistoryItem(
            execution_id=execution.id,
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            strategy=execution.strategy,
            status=execution.status,
            started_at=execution.started_at,
            ended_at=execution.ended_at,
            report=report,
        )
        for execution, scenario, report in rows
    ]


@router.post(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/report",
    response_model=ExecutionReportResponse,
    status_code=201,
)
def create_execution_report_endpoint(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> ExecutionReport:
    _owned_project(db, project_id, user)
    _scenario(db, project_id, scenario_id)
    execution = _execution(db, scenario_id, execution_id)
    report = generate_execution_report(db, execution)
    db.commit()
    db.refresh(report)
    return report


@router.get(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/report",
    response_model=ExecutionReportResponse,
)
def get_execution_report_endpoint(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ExecutionReport:
    _project(db, project_id)
    _scenario(db, project_id, scenario_id)
    _execution(db, scenario_id, execution_id)
    report = db.scalar(
        select(ExecutionReport).where(ExecutionReport.execution_id == execution_id)
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Execution report not found")
    return report


@router.post(
    "/{project_id}/reports/comparisons",
    response_model=ComparisonReportResponse,
    status_code=201,
)
def create_comparison(
    project_id: UUID,
    request: ComparisonCreateRequest,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> ComparisonReportResponse:
    _owned_project(db, project_id, user)
    comparison = create_comparison_report(
        db,
        project_id=project_id,
        created_by=user.id,
        name=request.name,
        execution_ids=request.execution_ids,
    )
    return _comparison_response(db, comparison)


@router.get(
    "/{project_id}/reports/comparisons",
    response_model=list[ComparisonReportResponse],
)
def list_comparisons(
    project_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[ComparisonReportResponse]:
    _project(db, project_id)
    comparisons = list(
        db.scalars(
            select(ComparisonReport)
            .where(ComparisonReport.project_id == project_id)
            .order_by(ComparisonReport.generated_at.desc())
        )
    )
    return [_comparison_response(db, comparison) for comparison in comparisons]


@router.get(
    "/{project_id}/reports/comparisons/{comparison_id}",
    response_model=ComparisonReportResponse,
)
def get_comparison(
    project_id: UUID,
    comparison_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ComparisonReportResponse:
    _project(db, project_id)
    comparison = db.scalar(
        select(ComparisonReport).where(
            ComparisonReport.id == comparison_id,
            ComparisonReport.project_id == project_id,
        )
    )
    if comparison is None:
        raise HTTPException(status_code=404, detail="Comparison report not found")
    return _comparison_response(db, comparison)
