from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import asyncio

from app.db.session import get_db
from app.db.types import ExecutionStatus
from app.modules.auth.api import current_user, qa_user
from app.modules.auth.models import User
from app.modules.load_tests import engine as load_engine
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.load_tests.schemas import (
    ExecutionCancelRequest,
    ExecutionCreateRequest,
    ExecutionResponse,
    MetricWindowResponse,
    ScenarioResponse,
    ScenarioWrite,
)
from app.modules.metrics.models import MetricWindow
from app.modules.projects.models import Endpoint, Project


router = APIRouter(prefix="/projects", tags=["load-tests"])


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


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Private helpers ---------------------------------------------------------


def _project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _owned_project(db: Session, project_id: UUID, user: User) -> Project:
    project = _project(db, project_id)
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Project owner required")
    return project


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


def _scenario(db: Session, project_id: UUID, scenario_id: UUID) -> TestScenario:
    scenario = db.scalar(
        select(TestScenario).where(
            TestScenario.id == scenario_id, TestScenario.project_id == project_id
        )
    )
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


def _execution(db: Session, scenario_id: UUID, execution_id: UUID) -> TestExecution:
    execution = db.scalar(
        select(TestExecution).where(
            TestExecution.id == execution_id,
            TestExecution.scenario_id == scenario_id,
        )
    )
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


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
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[TestScenario]:
    _project(db, project_id)
    return list(
        db.scalars(
            select(TestScenario)
            .where(TestScenario.project_id == project_id)
            .order_by(TestScenario.created_at, TestScenario.id)
        )
    )


@router.post(
    "/{project_id}/scenarios", response_model=ScenarioResponse, status_code=201
)
def create_scenario(
    project_id: UUID,
    request: ScenarioWrite,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> TestScenario:
    _owned_project(db, project_id, user)
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
    _project(db, project_id)
    return _scenario(db, project_id, scenario_id)


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
    _owned_project(db, project_id, user)
    scenario = _scenario(db, project_id, scenario_id)
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
    _owned_project(db, project_id, user)
    scenario = _scenario(db, project_id, scenario_id)
    db.delete(scenario)
    _commit(db, "Remove dependent executions before deleting the scenario")


# --- Execution creation and read --------------------------------------------

_SNAPSHOT_FIELDS = (
    "strategy",
    "duration_seconds",
    "initial_concurrency",
    "max_concurrency",
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
    _project(db, project_id)
    _scenario(db, project_id, scenario_id)
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
    _owned_project(db, project_id, user)
    scenario = _scenario(db, project_id, scenario_id)
    snapshot = {field: getattr(scenario, field) for field in _SNAPSHOT_FIELDS}
    execution = TestExecution(
        scenario_id=scenario.id,
        initiated_by=user.id,
        status=ExecutionStatus.PENDING,
        authorization_acknowledged=request.authorization_acknowledged,
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
    _project(db, project_id)
    _scenario(db, project_id, scenario_id)
    return _execution(db, scenario_id, execution_id)


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
    _project(db, project_id)
    _scenario(db, project_id, scenario_id)
    _execution(db, scenario_id, execution_id)
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
    _owned_project(db, project_id, user)
    _scenario(db, project_id, scenario_id)
    return _execution(db, scenario_id, execution_id)


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
    _ensure_transition(execution.status, ExecutionStatus.RUNNING)
    execution.status = ExecutionStatus.RUNNING
    execution.started_at = _now()
    _commit(db, "Execution could not be started")
    db.refresh(execution)
    if ENGINE_ENABLED:
        cancel_event = load_engine.registry.register(execution.id)
        asyncio.create_task(load_engine.run_execution(execution.id, cancel_event))
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
