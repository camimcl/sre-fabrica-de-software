from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import ControlStrategy


class ExecutionReport(Base):
    __tablename__ = "execution_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_executions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    total_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    successful_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    average_throughput_rps: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False
    )
    final_latency_p95_ms: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False
    )
    final_error_rate: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ComparisonReport(Base):
    __tablename__ = "comparison_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    repetitions_per_strategy: Mapped[int] = mapped_column(Integer, nullable=False)
    conditions_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    conditions_json: Mapped[str] = mapped_column(Text, nullable=False)
    results_json: Mapped[str] = mapped_column(Text, nullable=False)
    conclusion: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ComparisonReportExecution(Base):
    __tablename__ = "comparison_report_executions"
    __table_args__ = (
        UniqueConstraint(
            "comparison_report_id",
            "execution_id",
            name="uq_comparison_report_execution",
        ),
        UniqueConstraint(
            "comparison_report_id",
            "strategy",
            "repetition_number",
            name="uq_comparison_strategy_repetition",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comparison_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comparison_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    strategy: Mapped[ControlStrategy] = mapped_column(
        Enum(ControlStrategy, name="control_strategy", create_type=False),
        nullable=False,
    )
    repetition_number: Mapped[int] = mapped_column(Integer, nullable=False)
