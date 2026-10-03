from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.types import ControlAction, ControlStrategy, ModelStatus


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: str
    algorithm: str
    status: ModelStatus
    precision_score: Decimal | None
    recall_score: Decimal | None
    f1_score: Decimal | None
    accuracy_score: Decimal | None
    training_sample_count: int
    training_dataset_hash: str
    artifact_sha256: str
    notes: str | None
    created_at: datetime


class RiskPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metric_window_id: UUID
    model_version_id: UUID
    risk_probability: Decimal
    predicted_degradation: bool
    inference_latency_ms: int
    created_at: datetime


class ControlDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    metric_window_id: UUID
    risk_prediction_id: UUID | None
    strategy: ControlStrategy
    action: ControlAction
    previous_concurrency: int
    next_concurrency: int
    reason: str
    created_at: datetime
