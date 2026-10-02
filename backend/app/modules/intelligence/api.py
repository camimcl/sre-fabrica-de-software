from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.types import ModelStatus
from app.modules.auth.api import current_user, qa_user
from app.modules.auth.models import User
from app.modules.control.models import ControlDecision
from app.modules.intelligence.models import ModelVersion, RiskPrediction
from app.modules.intelligence.schemas import (
    ControlDecisionResponse,
    ModelVersionResponse,
    RiskPredictionResponse,
)
from app.modules.intelligence.training import (
    TrainingDataError,
    approve_candidate,
    train_candidate,
)
from app.modules.load_tests.api import _execution, _project, _scenario
from app.modules.metrics.models import MetricWindow


router = APIRouter(prefix="/intelligence", tags=["intelligence"])
execution_router = APIRouter(prefix="/projects", tags=["intelligence"])


@router.get("/models", response_model=list[ModelVersionResponse])
def list_models(
    _: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[ModelVersion]:
    return list(
        db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc()))
    )


@router.post("/models/train", response_model=ModelVersionResponse, status_code=201)
def train_model(
    _: User = Depends(qa_user), db: Session = Depends(get_db)
) -> ModelVersion:
    try:
        return train_candidate(db)
    except TrainingDataError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/models/{model_id}/approve", response_model=ModelVersionResponse
)
def approve_model(
    model_id: UUID,
    _: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> ModelVersion:
    model = db.get(ModelVersion, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model version not found")
    if model.status == ModelStatus.RETIRED:
        raise HTTPException(status_code=409, detail="A retired model cannot be approved")
    try:
        return approve_candidate(db, model)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Model approval changed concurrently; reload and retry") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _execution_windows(
    db: Session,
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
) -> list[UUID]:
    _project(db, project_id)
    _scenario(db, project_id, scenario_id)
    _execution(db, scenario_id, execution_id)
    return list(
        db.scalars(
            select(MetricWindow.id).where(MetricWindow.execution_id == execution_id)
        )
    )


@execution_router.get(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/risk-predictions",
    response_model=list[RiskPredictionResponse],
)
def list_predictions(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[RiskPrediction]:
    window_ids = _execution_windows(db, project_id, scenario_id, execution_id)
    if not window_ids:
        return []
    return list(
        db.scalars(
            select(RiskPrediction)
            .where(RiskPrediction.metric_window_id.in_(window_ids))
            .order_by(RiskPrediction.created_at)
        )
    )


@execution_router.get(
    "/{project_id}/scenarios/{scenario_id}/executions/{execution_id}/control-decisions",
    response_model=list[ControlDecisionResponse],
)
def list_decisions(
    project_id: UUID,
    scenario_id: UUID,
    execution_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[ControlDecision]:
    window_ids = _execution_windows(db, project_id, scenario_id, execution_id)
    if not window_ids:
        return []
    return list(
        db.scalars(
            select(ControlDecision)
            .where(ControlDecision.metric_window_id.in_(window_ids))
            .order_by(ControlDecision.created_at)
        )
    )
