from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import asyncio
from datetime import datetime as _datetime

from app.core.query import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    escape_like,
    normalized_search,
    paginate,
    validate_date_range,
)
from app.db.session import get_db
from app.db.types import ControlStrategy, ExecutionStatus
from app.modules.auth.api import current_user, qa_user
from app.modules.auth.models import User
from app.modules.load_tests import engine as load_engine
from app.modules.load_tests.access import require_execution, require_scenario
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.load_tests.target import capture_target, resolve_execution_target
from app.modules.load_tests.schemas import (
    ExecutionCancelRequest,
    ExecutionCreateRequest,
    ExecutionPage,
    ExecutionResponse,
    MetricWindowResponse,
    ScenarioResponse,
    ScenarioWrite,
)
from app.modules.metrics.models import MetricWindow
from app.modules.projects.access import require_owned_project, require_project
from app.modules.projects.models import Endpoint


router = APIRouter(prefix="/projects", tags=["load-tests"])


# --- Aggregated executions query (filters, search, pagination) --------------


@router.get("/{project_id}/executions", response_model=ExecutionPage)
def query_project_executions(
    project_id: UUID,
    status: ExecutionStatus | None = Query(None),
    strategy: ControlStrategy | None = Query(None),
    initiated_by: UUID | None = Query(None),
    date_from: _datetime | None = Query(None),
    date_to: _datetime | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ExecutionPage:
    require_project(db, project_id)
    validate_date_range(date_from, date_to)
    statement = (
        select(TestExecution)
        .join(TestScenario, TestScenario.id == TestExecution.scenario_id)
        .where(TestScenario.project_id == project_id)
    )
    if status is not None:
        statement = statement.where(TestExecution.status == status)
    if strategy is not None:
        statement = statement.where(TestExecution.strategy == strategy)
    if initiated_by is not None:
        statement = statement.where(TestExecution.initiated_by == initiated_by)
    if date_from is not None:
        statement = statement.where(TestExecution.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(TestExecution.created_at <= date_to)
    term = normalized_search(search)
    if term is not None:
        statement = statement.where(
            TestScenario.name.ilike(f"%{escape_like(term)}%", escape="\\")
        )
    statement = statement.order_by(
        TestExecution.created_at.desc(), TestExecution.id.desc()
    )
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return ExecutionPage(items=items, total=total, page=page, page_size=page_size)


# --- Execution state machine -------------------------------------------------

ALLOWED_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {ExecutionStatus.RUNNING, ExecutionStatus.CANCELLED},
    ExecutionStatus.RUNNING: {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.FAILED,
    },
    ExecutionStatus.COMPLETED: set(),
    ExecutionStatus.CANCELLED: set(),
    ExecutionStatus.FAILED: set(),
}


def _ensure_transition(current: ExecutionStatus, target: ExecutionStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise HTTPException(
            status_code=409, detail="Invalid execution state transition"
        )


# When True (default), starting an execution launches the real load engine
# (Phase B). Tests that exercise manual state transitions (Phase A) disable it.
ENGINE_ENABLED = True


def _reject_if_engine_active(execution_id: UUID) -> None:
    """Block manual completion/failure while the engine is driving the run.

    The engine owns the terminal transition of a RUNNING execution it started;
    allowing a manual /complete or /fail here would race with the engine and
    could leave traffic still being generated after a "terminal" state.
    """
    if ENGINE_ENABLED and load_engine.registry.is_running(execution_id):
        raise HTTPException(
            status_code=409,
            detail="Execution is being driven by the load engine; cancel it instead",
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Private helpers ---------------------------------------------------------


def _authorized_endpoint(db: Session, project_id: UUID, endpoint_id: UUID) -> Endpoint:
    endpoint = db.scalar(
        select(Endpoint).where(
            Endpoint.id == endpoint_id, Endpoint.project_id == project_id
        )
    )
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    if not endpoint.authorization_confirmed:
        raise HTTPException(
            status_code=409,
            detail=(
                "The target endpoint must have confirmed authorization "
                "before scenarios can target it"
            ),
        )
    return endpoint


def _commit(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


# --- Scenario CRUD -----------------------------------------------------------


@router.get("/{project_id}/scenarios", response_model=list[ScenarioResponse])
def list_scenarios(
    project_id: UUID,
    search: str | None = Query(None),
    strategy: ControlStrategy | None = Query(None),
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[TestScenario]:
    require_project(db, project_id)
    statement = (
        select(TestScenario)
        .where(TestScenario.project_id == project_id)
        .order_by(TestScenario.created_at, TestScenario.id)
    )
    if strategy is not None:
        statement = statement.where(TestScenario.strategy == strategy)
    term = normalized_search(search)
    if term is not None:
        statement = statement.where(
            TestScenario.name.ilike(f"%{escape_like(term)}%", escape="\\")
        )
    return list(db.scalars(statement))


@router.post(
    "/{project_id}/scenarios", response_model=ScenarioResponse, status_code=201
)
def create_scenario(
    project_id: UUID,
    request: ScenarioWrite,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> TestScenario:
    require_owned_project(db, project_id, user)
    _authorized_endpoint(db, project_id, request.endpoint_id)
    scenario = TestScenario(
        project_id=project_id, created_by=user.id, **request.model_dump()
    )
    db.add(scenario)
    _commit(db, "Scenario could not be created")
    db.refresh(scenario)
    return scenario


@router.get(
    "/{project_id}/scenarios/{scenario_id}", response_model=ScenarioResponse
)
def get_scenario(
    project_id: UUID,
    scenario_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> TestScenario:
    require_project(db, project_id)
    return require_scenario(db, project_id, scenario_id)


@router.put(
    "/{project_id}/scenarios/{scenario_id}", response_model=ScenarioResponse
)
def update_scenario(
    project_id: UUID,
    scenario_id: UUID,
    request: ScenarioWrite,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> TestScenario:
    require_owned_project(db, project_id, user)
    scenario = require_scenario(db, project_id, scenario_id)
    _authorized_endpoint(db, project_id, request.endpoint_id)
    for key, value in request.model_dump().items():
        setattr(scenario, key, value)
    _commit(db, "Scenario could not be updated")
    db.refresh(scenario)
    return scenario


@router.delete("/{project_id}/scenarios/{scenario_id}", status_code=204)
def delete_scenario(
    project_id: UUID,
    scenario_id: UUID,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> None:
    require_owned_project(db, project_id, user)
    scenario = require_scenario(db, project_id, scenario_id)
    db.delete(scenario)
    _commit(db, "Remove dependent executions before deleting the scenario")


# --- Execution creation and read --------------------------------------------

_SNAPSHOT_FIELDS = (
    "strategy",
    "duration_seconds",
    "initial_concurrency",
    "max_concurrency",
    "ramp_up_per_window",
    "timeout_ms",
    "p95_limit_ms",
    "error_rate_limit",
)


@router.get(
    "/{project_id}/scenarios/{scenario_id}/executions",
    response_model=list[ExecutionResponse],
)
def list_executions(
    project_id: UUID,
    scenario_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[TestExecution]:
    require_project(db, project_id)
    require_scenario(db, project_id, scenario_id)
    return list(
        db.scalars(
            select(TestExecution)
            .where(TestExecution.scenario_id == scenario_id)
            .order_by(TestExecution.created_at, TestExecution.id)
        )
    )


@router.post(
    "/{project_id}/scenarios/{scenario_id}/executions",
    response_model=ExecutionResponse,
    status_code=201,
)
def create_execution(
    project_id: UUID,
    scenario_id: UUID,
    request: ExecutionCreateRequest,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    require_owned_project(db, project_id, user)
    scenario = require_scenario(db, project_id, scenario_id)
    snapshot = {field: getattr(scenario, field) for field in _SNAPSHOT_FIELDS}
    endpoint = _authorized_endpoint(db, project_id, scenario.endpoint_id)
    execution = TestExecution(
        scenario_id=scenario.id,
        initiated_by=user.id,
        status=ExecutionStatus.PENDING,
        authorization_acknowledged=request.authorization_acknowledged,
        target_snapshot=capture_target(endpoint),
        **snapshot,
    )
    db.add(execution)
    _commit(db, "Execution could not be created")
    db.refresh(execution)
    return execution


@router.get(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}",
    response_model=ExecutionResponse,
)
def get_execution(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    require_project(db, project_id)
    require_scenario(db, project_id, scenario_id)
    return require_execution(db, scenario_id, execution_id)


@router.get(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/metric-windows",
    response_model=list[MetricWindowResponse],
)
def list_metric_windows(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[MetricWindow]:
    require_project(db, project_id)
    require_scenario(db, project_id, scenario_id)
    require_execution(db, scenario_id, execution_id)
    return list(
        db.scalars(
            select(MetricWindow)
            .where(MetricWindow.execution_id == execution_id)
            .order_by(MetricWindow.sequence_number)
        )
    )


# --- Execution lifecycle transitions ----------------------------------------


def _load_owned_execution(
    db: Session, project_id: UUID, scenario_id: UUID, execution_id: UUID, user: User
) -> TestExecution:
    require_owned_project(db, project_id, user)
    require_scenario(db, project_id, scenario_id)
    return require_execution(db, scenario_id, execution_id)


@router.post(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/start",
    response_model=ExecutionResponse,
)
async def start_execution(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    execution = _load_owned_execution(db, project_id, scenario_id, execution_id, user)
    if not execution.authorization_acknowledged:
        raise HTTPException(
            status_code=409,
            detail="authorization_acknowledged must be true to start an execution",
        )
    # Revalidate the target authorization now: it may have been revoked after
    # the scenario/execution was created. Fail fast and clearly here instead of
    # letting the engine move the execution to FAILED asynchronously.
    try:
        resolve_execution_target(db, execution)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _ensure_transition(execution.status, ExecutionStatus.RUNNING)
    execution.status = ExecutionStatus.RUNNING
    execution.started_at = _now()
    _commit(db, "Execution could not be started")
    db.refresh(execution)
    if ENGINE_ENABLED:
        cancel_event = load_engine.registry.register(execution.id)
        task = asyncio.create_task(
            load_engine.run_execution(execution.id, cancel_event)
        )
        load_engine.registry.track_task(execution.id, task)
    return execution


@router.post(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/complete",
    response_model=ExecutionResponse,
)
def complete_execution(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    execution = _load_owned_execution(db, project_id, scenario_id, execution_id, user)
    _reject_if_engine_active(execution.id)
    _ensure_transition(execution.status, ExecutionStatus.COMPLETED)
    execution.status = ExecutionStatus.COMPLETED
    execution.ended_at = _now()
    _commit(db, "Execution could not be completed")
    db.refresh(execution)
    return execution


@router.post(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/fail",
    response_model=ExecutionResponse,
)
def fail_execution(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    execution = _load_owned_execution(db, project_id, scenario_id, execution_id, user)
    _reject_if_engine_active(execution.id)
    _ensure_transition(execution.status, ExecutionStatus.FAILED)
    execution.status = ExecutionStatus.FAILED
    execution.ended_at = _now()
    _commit(db, "Execution could not be marked as failed")
    db.refresh(execution)
    return execution


@router.post(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/cancel",
    response_model=ExecutionResponse,
)
async def cancel_execution(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    request: ExecutionCancelRequest,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    execution = _load_owned_execution(db, project_id, scenario_id, execution_id, user)
    _ensure_transition(execution.status, ExecutionStatus.CANCELLED)
    # If the engine is actively driving this execution, signal it to stop and
    # let it finalize state (effective emergency stop). Otherwise cancel here.
    if ENGINE_ENABLED and load_engine.registry.is_running(execution.id):
        load_engine.registry.cancel(execution.id)
        execution.cancellation_reason = request.cancellation_reason
        _commit(db, "Execution could not be cancelled")
        db.refresh(execution)
        return execution
    execution.status = ExecutionStatus.CANCELLED
    execution.cancellation_reason = request.cancellation_reason
    execution.ended_at = _now()
    _commit(db, "Execution could not be cancelled")
    db.refresh(execution)
    return execution
