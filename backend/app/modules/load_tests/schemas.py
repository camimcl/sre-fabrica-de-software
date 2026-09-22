from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.types import ControlStrategy, ExecutionStatus


class ScenarioWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    endpoint_id: UUID
    duration_seconds: int = Field(ge=1)
    initial_concurrency: int = Field(ge=1)
    max_concurrency: int = Field(ge=1)
    ramp_up_per_window: int = Field(ge=0)
    timeout_ms: int = Field(ge=1)
    strategy: ControlStrategy
    p95_limit_ms: int = Field(ge=1)
    error_rate_limit: Decimal = Field(ge=0, le=1)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Scenario name is required")
        if len(cleaned) > 120:
            raise ValueError("Scenario name cannot exceed 120 characters")
        return cleaned

    @model_validator(mode="after")
    def validate_concurrency(self):
        if self.initial_concurrency > self.max_concurrency:
            raise ValueError(
                "initial_concurrency must be less than or equal to max_concurrency"
            )
        return self


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    endpoint_id: UUID
    created_by: UUID
    name: str
    duration_seconds: int
    initial_concurrency: int
    max_concurrency: int
    ramp_up_per_window: int
    timeout_ms: int
    strategy: ControlStrategy
    p95_limit_ms: int
    error_rate_limit: Decimal
    created_at: datetime


class ExecutionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorization_acknowledged: bool = False

    @field_validator("authorization_acknowledged")
    @classmethod
    def must_acknowledge(cls, value: bool) -> bool:
        if not value:
            raise ValueError(
                "authorization_acknowledged must be true to create an execution"
            )
        return value


class ExecutionCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cancellation_reason: str = Field(min_length=1, max_length=500)

    @field_validator("cancellation_reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("cancellation_reason is required")
        return cleaned


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scenario_id: UUID
    initiated_by: UUID
    model_version_id: UUID | None
    status: ExecutionStatus
    strategy: ControlStrategy
    duration_seconds: int
    initial_concurrency: int
    max_concurrency: int
    timeout_ms: int
    p95_limit_ms: int
    error_rate_limit: Decimal
    authorization_acknowledged: bool
    started_at: datetime | None
    ended_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
