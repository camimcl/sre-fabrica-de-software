from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.types import ControlStrategy, ExecutionStatus


class ExecutionReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    execution_id: UUID
    total_requests: int
    successful_requests: int
    average_throughput_rps: Decimal
    final_latency_p95_ms: Decimal
    final_error_rate: Decimal
    summary: str | None
    generated_at: datetime


class ExecutionHistoryItem(BaseModel):
    execution_id: UUID
    scenario_id: UUID
    scenario_name: str
    strategy: ControlStrategy
    status: ExecutionStatus
    started_at: datetime | None
    ended_at: datetime | None
    report: ExecutionReportResponse | None


class ComparisonCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    execution_ids: list[UUID] = Field(min_length=9, max_length=90)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Comparison name is required")
        return cleaned

    @field_validator("execution_ids")
    @classmethod
    def unique_executions(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Execution identifiers must be unique")
        return value


class ComparisonReportResponse(BaseModel):
    id: UUID
    project_id: UUID
    created_by: UUID
    name: str
    repetitions_per_strategy: int
    conditions_fingerprint: str
    conditions: dict[str, Any]
    results: dict[str, Any]
    conclusion: str
    execution_ids: list[UUID]
    generated_at: datetime
