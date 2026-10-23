import csv
import io
import json
from datetime import datetime as _datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.query import (
    escape_like,
    normalized_range,
    normalized_search,
)
from app.db.session import get_db
from app.db.types import ControlStrategy, ExecutionStatus
from app.modules.auth.api import current_user
from app.modules.auth.models import User
from app.modules.load_tests.access import require_execution, require_scenario
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.projects.access import require_project
from app.modules.reports.models import ComparisonReport, ExecutionReport


router = APIRouter(prefix="/projects", tags=["exports"])

STRATEGIES = (ControlStrategy.FIXED, ControlStrategy.RULES, ControlStrategy.AI_HYBRID)

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_cell(value: object) -> object:
    """Neutralize spreadsheet formula injection in textual cells.

    Numeric values are returned unchanged. Strings that begin with a character
    a spreadsheet may interpret as a formula are prefixed with a single quote,
    which spreadsheets render as plain text.
    """
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return value
    text = "" if value is None else str(value)
    if text and text[0] in _FORMULA_PREFIXES:
        return "'" + text
    return text


def _csv_response(rows: list[list], header: list[str], filename: str) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow([_sanitize_cell(cell) for cell in row])
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
    initiated_by: UUID | None = Query(None),
    date_from: _datetime | None = Query(None),
    date_to: _datetime | None = Query(None),
    search: str | None = Query(None),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_project(db, project_id)
    start, end = normalized_range(date_from, date_to)
    statement = (
        select(TestExecution, TestScenario)
        .join(TestScenario, TestScenario.id == TestExecution.scenario_id)
        .where(TestScenario.project_id == project_id)
    )
    if status is not None:
        statement = statement.where(TestExecution.status == status)
    if strategy is not None:
        statement = statement.where(TestExecution.strategy == strategy)
    if initiated_by is not None:
        statement = statement.where(TestExecution.initiated_by == initiated_by)
    if start is not None:
        statement = statement.where(TestExecution.created_at >= start)
    if end is not None:
        statement = statement.where(TestExecution.created_at <= end)
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


def _wrap_line(text: str, font: str, size: float, max_width: float) -> list[str]:
    """Wrap a single logical line into physical lines fitting max_width.

    Preserves whole words; falls back to character splitting for tokens longer
    than the available width so no content is silently truncated.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth

    if not text:
        return [""]
    wrapped: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = word if not current else f"{current} {word}"
        if stringWidth(candidate, font, size) <= max_width:
            current = candidate
            continue
        if current:
            wrapped.append(current)
            current = ""
        # Word itself may exceed the width: break it by characters.
        while stringWidth(word, font, size) > max_width:
            cut = len(word)
            while cut > 1 and stringWidth(word[:cut], font, size) > max_width:
                cut -= 1
            wrapped.append(word[:cut])
            word = word[cut:]
        current = word
    wrapped.append(current)
    return wrapped


def _pdf_response(title: str, lines: list[str], filename: str) -> StreamingResponse:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 2 * cm
    max_width = width - 4 * cm
    body_font, body_size = "Helvetica", 11
    y = height - 2 * cm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, y, title)
    y -= 1 * cm
    pdf.setFont(body_font, body_size)

    def _new_page() -> float:
        pdf.showPage()
        pdf.setFont(body_font, body_size)
        return height - 2 * cm

    for logical in lines:
        for physical in _wrap_line(logical, body_font, body_size, max_width):
            if y < 2 * cm:
                y = _new_page()
            pdf.drawString(left, y, physical)
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
    require_scenario(db, project_id, scenario_id)
    require_execution(db, scenario_id, execution_id)
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
