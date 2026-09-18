from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import ControlStrategy, ExecutionStatus


class TestScenario(Base):
    __tablename__ = "test_scenarios"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "endpoint_id"],
            ["endpoints.project_id", "endpoints.id"],
            name="fk_scenario_endpoint_project",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    endpoint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    ramp_up_per_window: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy: Mapped[ControlStrategy] = mapped_column(
        Enum(ControlStrategy, name="control_strategy"), nullable=False
    )
    p95_limit_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_rate_limit: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TestExecution(Base):
    __tablename__ = "test_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_scenarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    initiated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id", ondelete="RESTRICT")
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, name="execution_status"), nullable=False
    )
    strategy: Mapped[ControlStrategy] = mapped_column(
        Enum(ControlStrategy, name="control_strategy"), nullable=False
    )
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    initial_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    p95_limit_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    error_rate_limit: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    authorization_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
