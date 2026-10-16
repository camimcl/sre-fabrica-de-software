from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from statistics import fmean, pstdev
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.types import ControlStrategy, ExecutionStatus
from app.modules.control.models import ControlDecision
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.metrics.models import MetricWindow
from app.modules.reports.models import (
    ComparisonReport,
    ComparisonReportExecution,
    ExecutionReport,
)


MIN_REPETITIONS_PER_STRATEGY = 3
STRATEGIES = (
    ControlStrategy.FIXED,
    ControlStrategy.RULES,
    ControlStrategy.AI_HYBRID,
)


def _decimal(value: float, places: str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _summary_values(report: ExecutionReport) -> dict:
    try:
        return json.loads(report.summary or "{}")
    except json.JSONDecodeError:
        return {}


def generate_execution_report(db: Session, execution: TestExecution) -> ExecutionReport:
    if execution.status not in {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.FAILED,
    }:
        raise HTTPException(
            status_code=409, detail="Only terminal executions can be reported"
        )
    windows = list(
        db.scalars(
            select(MetricWindow)
            .where(MetricWindow.execution_id == execution.id)
            .order_by(MetricWindow.sequence_number)
        )
    )
    if not windows:
        raise HTTPException(
            status_code=409, detail="Execution has no metric windows to report"
        )

    total_requests = sum(window.request_count for window in windows)
    successful_requests = sum(window.success_count for window in windows)
    total_timeouts = sum(window.timeout_count for window in windows)
    observed_duration_ms = sum(window.window_duration_ms for window in windows)
    average_throughput = (
        total_requests / (observed_duration_ms / 1000)
        if observed_duration_ms
        else 0.0
    )
    aggregate_error_rate = (
        (total_requests - successful_requests) / total_requests
        if total_requests
        else 0.0
    )
    p95_values = [float(window.latency_p95_ms) for window in windows]
    compliant_windows = sum(
        1
        for window in windows
        if float(window.latency_p95_ms) < execution.p95_limit_ms
        and float(window.error_rate) < float(execution.error_rate_limit)
    )
    summary = json.dumps(
        {
            "window_count": len(windows),
            "observed_duration_ms": observed_duration_ms,
            "total_timeouts": total_timeouts,
            "peak_concurrency": max(window.concurrency for window in windows),
            "mean_latency_p95_ms": fmean(p95_values),
            "max_latency_p95_ms": max(p95_values),
            "compliant_windows": compliant_windows,
            "compliance_rate": compliant_windows / len(windows),
        },
        sort_keys=True,
    )
    report = db.scalar(
        select(ExecutionReport).where(ExecutionReport.execution_id == execution.id)
    )
    values = {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "average_throughput_rps": _decimal(average_throughput, "0.0001"),
        "final_latency_p95_ms": windows[-1].latency_p95_ms,
        "final_error_rate": _decimal(aggregate_error_rate, "0.00001"),
        "summary": summary,
    }
    if report is None:
        report = ExecutionReport(execution_id=execution.id, **values)
        db.add(report)
    else:
        for key, value in values.items():
            setattr(report, key, value)
    db.flush()
    return report


def _conditions(execution: TestExecution) -> dict:
    try:
        target = json.loads(execution.target_snapshot or "null")
    except (TypeError, json.JSONDecodeError):
        target = None
    required = {"endpoint_id", "base_url", "http_method", "window_duration_ms"}
    if not isinstance(target, dict) or not required <= target.keys():
        raise HTTPException(
            status_code=409,
            detail="Execution has no recorded target snapshot; run a new experiment",
        )
    return {
        "target": target,
        "duration_seconds": execution.duration_seconds,
        "initial_concurrency": execution.initial_concurrency,
        "max_concurrency": execution.max_concurrency,
        "ramp_up_per_window": execution.ramp_up_per_window,
        "timeout_ms": execution.timeout_ms,
        "p95_limit_ms": execution.p95_limit_ms,
        "error_rate_limit": str(execution.error_rate_limit),
    }


def _metric_stats(values: list[float]) -> dict[str, float]:
    return {
        "mean": round(fmean(values), 5),
        "standard_deviation": round(pstdev(values), 5),
        "minimum": round(min(values), 5),
        "maximum": round(max(values), 5),
    }


def _relative_change(candidate: float, baseline: float) -> float | None:
    if baseline == 0:
        return None
    return round(((candidate - baseline) / baseline) * 100, 3)


def _comparison_results(
    grouped: dict[ControlStrategy, list[ExecutionReport]],
) -> tuple[dict, str]:
    results: dict[str, dict] = {}
    for strategy in STRATEGIES:
        reports = grouped[strategy]
        summaries = [_summary_values(report) for report in reports]
        results[strategy.value] = {
            "runs": len(reports),
            "throughput_rps": _metric_stats(
                [float(report.average_throughput_rps) for report in reports]
            ),
            "latency_p95_ms": _metric_stats(
                [
                    float(
                        summary.get(
                            "mean_latency_p95_ms", report.final_latency_p95_ms
                        )
                    )
                    for report, summary in zip(reports, summaries)
                ]
            ),
            "error_rate": _metric_stats(
                [float(report.final_error_rate) for report in reports]
            ),
            "total_requests": sum(report.total_requests for report in reports),
            "successful_requests": sum(report.successful_requests for report in reports),
            "timeouts": sum(int(summary.get("total_timeouts", 0)) for summary in summaries),
            "peak_concurrency": max(
                int(summary.get("peak_concurrency", 0)) for summary in summaries
            ),
            "compliance_rate": _metric_stats(
                [float(summary.get("compliance_rate", 0)) for summary in summaries]
            ),
        }

    ai = results[ControlStrategy.AI_HYBRID.value]
    comparisons = {}
    for baseline_name in (ControlStrategy.FIXED.value, ControlStrategy.RULES.value):
        baseline = results[baseline_name]
        comparisons[f"AI_HYBRID_vs_{baseline_name}"] = {
            "throughput_change_percent": _relative_change(
                ai["throughput_rps"]["mean"], baseline["throughput_rps"]["mean"]
            ),
            "latency_p95_change_percent": _relative_change(
                ai["latency_p95_ms"]["mean"], baseline["latency_p95_ms"]["mean"]
            ),
            "error_rate_change_percent": _relative_change(
                ai["error_rate"]["mean"], baseline["error_rate"]["mean"]
            ),
        }
    results["comparisons"] = comparisons
    conclusion = (
        "Descriptive comparison generated from equivalent repeated executions. "
        "Positive throughput deltas favor AI_HYBRID; negative latency and error "
        "deltas favor AI_HYBRID. Dispersion is reported and no statistical "
        "significance or production generalization is implied."
    )
    return results, conclusion


def create_comparison_report(
    db: Session,
    *,
    project_id: UUID,
    created_by: UUID,
    name: str,
    execution_ids: list[UUID],
) -> ComparisonReport:
    rows = db.execute(
        select(TestExecution, TestScenario)
        .join(TestScenario, TestScenario.id == TestExecution.scenario_id)
        .where(
            TestExecution.id.in_(execution_ids),
            TestScenario.project_id == project_id,
        )
        .order_by(TestExecution.created_at, TestExecution.id)
    ).all()
    if len(rows) != len(execution_ids):
        raise HTTPException(
            status_code=404,
            detail="One or more executions do not belong to this project",
        )

    grouped_executions: dict[ControlStrategy, list[TestExecution]] = defaultdict(list)
    canonical_conditions: dict | None = None
    for execution, scenario in rows:
        if execution.status != ExecutionStatus.COMPLETED:
            raise HTTPException(
                status_code=409,
                detail="Comparisons require completed executions",
            )
        conditions = _conditions(execution)
        if canonical_conditions is None:
            canonical_conditions = conditions
        elif conditions != canonical_conditions:
            raise HTTPException(
                status_code=409,
                detail="Executions must use equivalent endpoint and load conditions",
            )
        grouped_executions[execution.strategy].append(execution)

    counts = {strategy: len(grouped_executions[strategy]) for strategy in STRATEGIES}
    if any(count < MIN_REPETITIONS_PER_STRATEGY for count in counts.values()):
        raise HTTPException(
            status_code=409,
            detail=(
                "Comparisons require FIXED, RULES and AI_HYBRID with at least "
                f"{MIN_REPETITIONS_PER_STRATEGY} completed repetitions each"
            ),
        )
    if len(set(counts.values())) != 1:
        raise HTTPException(
            status_code=409,
            detail="Each strategy must have the same number of repetitions",
        )

    grouped_reports: dict[ControlStrategy, list[ExecutionReport]] = defaultdict(list)
    for strategy in STRATEGIES:
        for execution in grouped_executions[strategy]:
            grouped_reports[strategy].append(generate_execution_report(db, execution))

    assert canonical_conditions is not None
    encoded_conditions = json.dumps(canonical_conditions, sort_keys=True)
    results, conclusion = _comparison_results(grouped_reports)
    ai_executions = grouped_executions[ControlStrategy.AI_HYBRID]
    ai_ids = [execution.id for execution in ai_executions]
    decisions = db.execute(
        select(ControlDecision.strategy, ControlDecision.risk_prediction_id)
        .join(MetricWindow, MetricWindow.id == ControlDecision.metric_window_id)
        .where(MetricWindow.execution_id.in_(ai_ids))
    ).all()
    ai_windows = sum(_summary_values(report)["window_count"] for report in grouped_reports[ControlStrategy.AI_HYBRID])
    inferred = sum(strategy == ControlStrategy.AI_HYBRID and prediction is not None for strategy, prediction in decisions)
    fallback = sum(strategy == ControlStrategy.RULES for strategy, _ in decisions)
    results["ai_evidence"] = {
        "model_version_ids": sorted({str(execution.model_version_id) for execution in ai_executions if execution.model_version_id}),
        "windows": ai_windows,
        "inference_windows": inferred,
        "fallback_windows": fallback,
        "unverified_windows": ai_windows - inferred - fallback,
    }
    results["metric_definitions"] = {
        "latency_p95_ms": "Mean of per-window P95 values per execution, then statistics across repetitions; not a global P95.",
        "throughput_rps": "Requests divided by observed metric-window duration; excludes time between windows.",
        "standard_deviation": "Population standard deviation of the selected repetitions.",
    }
    if inferred != ai_windows:
        conclusion += " WARNING: AI_HYBRID includes fallback or unverified windows; differences cannot be attributed exclusively to AI inference."
    if len(results["ai_evidence"]["model_version_ids"]) != 1:
        conclusion += " WARNING: a single model version was not verified across AI_HYBRID runs."
    comparison = ComparisonReport(
        project_id=project_id,
        created_by=created_by,
        name=name,
        repetitions_per_strategy=next(iter(counts.values())),
        conditions_fingerprint=hashlib.sha256(encoded_conditions.encode()).hexdigest(),
        conditions_json=encoded_conditions,
        results_json=json.dumps(results, sort_keys=True),
        conclusion=conclusion,
    )
    db.add(comparison)
    db.flush()
    for strategy in STRATEGIES:
        for repetition, execution in enumerate(grouped_executions[strategy], start=1):
            db.add(
                ComparisonReportExecution(
                    comparison_report_id=comparison.id,
                    execution_id=execution.id,
                    strategy=strategy,
                    repetition_number=repetition,
                )
            )
    db.commit()
    db.refresh(comparison)
    return comparison
