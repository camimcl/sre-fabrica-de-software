import csv
import io
import json
from datetime import datetime as _datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.query import escape_like, normalized_search, validate_date_range
from app.db.session import get_db
from app.db.types import ControlStrategy, ExecutionStatus
from app.modules.auth.api import current_user
from app.modules.auth.models import User
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.projects.access import require_project
from app.modules.reports.models import ComparisonReport, ExecutionReport


router = APIRouter(prefix="/projects", tags=["exports"])

STRATEGIES = (ControlStrategy.FIXED, ControlStrategy.RULES, ControlStrategy.AI_HYBRID)


def _csv_response(rows: list[list], header: list[str], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/exports/executions.csv")
def export_executions_csv(
    project_id: UUID,
    status: ExecutionStatus | None = Query(None),
    strategy: ControlStrategy | None = Query(None),
    date_from: _datetime | None = Query(None),
    date_to: _datetime | None = Query(None),
    search: str | None = Query(None),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_project(db, project_id)
    validate_date_range(date_from, date_to)
    statement = (
        select(TestExecution, TestScenario)
        .join(TestScenario, TestScenario.id == TestExecution.scenario_id)
        .where(TestScenario.project_id == project_id)
    )
    if status is not None:
        statement = statement.where(TestExecution.status == status)
    if strategy is not None:
        statement = statement.where(TestExecution.strategy == strategy)
    if date_from is not None:
        statement = statement.where(TestExecution.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(TestExecution.created_at <= date_to)
    term = normalized_search(search)
    if term is not None:
        statement = statement.where(
            TestScenario.name.ilike(f"%{escape_like(term)}%", escape="\\")
        )
    statement = statement.order_by(TestExecution.created_at.desc())
    rows = []
    for execution, scenario in db.execute(statement).all():
        rows.append([
            str(execution.id),
            scenario.name,
            execution.strategy.value,
            execution.status.value,
            execution.started_at.isoformat() if execution.started_at else "",
            execution.ended_at.isoformat() if execution.ended_at else "",
            execution.created_at.isoformat(),
        ])
    header = [
        "execution_id", "scenario_name", "strategy", "status",
        "started_at", "ended_at", "created_at",
    ]
    return _csv_response(rows, header, "executions.csv")


@router.get("/{project_id}/reports/comparisons/{comparison_id}.csv")
def export_comparison_csv(
    project_id: UUID,
    comparison_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_project(db, project_id)
    comparison = db.scalar(
        select(ComparisonReport).where(
            ComparisonReport.id == comparison_id,
            ComparisonReport.project_id == project_id,
        )
    )
    if comparison is None:
        raise HTTPException(status_code=404, detail="Comparison report not found")
    results = json.loads(comparison.results_json)
    header = [
        "strategy", "runs", "throughput_rps_mean", "latency_p95_ms_mean",
        "error_rate_mean", "compliance_rate_mean",
    ]
    rows = []
    for strategy in STRATEGIES:
        result = results.get(strategy.value)
        if not result:
            continue
        rows.append([
            strategy.value,
            result.get("runs", 0),
            result.get("throughput_rps", {}).get("mean", 0),
            result.get("latency_p95_ms", {}).get("mean", 0),
            result.get("error_rate", {}).get("mean", 0),
            result.get("compliance_rate", {}).get("mean", 0),
        ])
    return _csv_response(rows, header, f"comparison-{comparison_id}.csv")


def _pdf_response(title: str, lines: list[str], filename: str) -> StreamingResponse:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _width, height = A4
    y = height - 2 * cm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, y, title)
    y -= 1 * cm
    pdf.setFont("Helvetica", 11)
    for line in lines:
        if y < 2 * cm:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 2 * cm
        pdf.drawString(2 * cm, y, line[:110])
        y -= 0.7 * cm
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/report.pdf"
)
def export_execution_report_pdf(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_project(db, project_id)
    report = db.scalar(
        select(ExecutionReport).where(ExecutionReport.execution_id == execution_id)
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Execution report not found")
    summary = json.loads(report.summary or "{}")
    lines = [
        f"Execution: {report.execution_id}",
        f"Total requests: {report.total_requests}",
        f"Successful requests: {report.successful_requests}",
        f"Average throughput (rps): {report.average_throughput_rps}",
        f"Final P95 latency (ms): {report.final_latency_p95_ms}",
        f"Final error rate: {report.final_error_rate}",
        f"Window count: {summary.get('window_count', 'n/a')}",
        f"Compliance rate: {summary.get('compliance_rate', 'n/a')}",
        f"Generated at: {report.generated_at.isoformat()}",
    ]
    return _pdf_response(
        "LoadForge - Execution Report", lines, f"execution-report-{execution_id}.pdf"
    )


@router.get("/{project_id}/reports/comparisons/{comparison_id}.pdf")
def export_comparison_pdf(
    project_id: UUID,
    comparison_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_project(db, project_id)
    comparison = db.scalar(
        select(ComparisonReport).where(
            ComparisonReport.id == comparison_id,
            ComparisonReport.project_id == project_id,
        )
    )
    if comparison is None:
        raise HTTPException(status_code=404, detail="Comparison report not found")
    results = json.loads(comparison.results_json)
    lines = [
        f"Name: {comparison.name}",
        f"Repetitions per strategy: {comparison.repetitions_per_strategy}",
        f"Conditions fingerprint: {comparison.conditions_fingerprint}",
        "",
        "Strategy results (throughput rps / P95 ms / error rate):",
    ]
    for strategy in STRATEGIES:
        result = results.get(strategy.value)
        if not result:
            continue
        lines.append(
            f"  {strategy.value}: "
            f"{result.get('throughput_rps', {}).get('mean', 0)} / "
            f"{result.get('latency_p95_ms', {}).get('mean', 0)} / "
            f"{result.get('error_rate', {}).get('mean', 0)}"
        )
    lines.append("")
    for line in (comparison.conclusion or "").split(". "):
        if line.strip():
            lines.append(line.strip())
    return _pdf_response(
        "LoadForge - Comparison Report", lines, f"comparison-{comparison_id}.pdf"
    )
