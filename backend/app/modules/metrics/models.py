from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MetricWindow(Base):
    __tablename__ = "metric_windows"
    __table_args__ = (
        UniqueConstraint(
            "execution_id", "sequence_number", name="uq_metric_window_sequence"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    window_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_count: Mapped[int] = mapped_column(Integer, nullable=False)
    throughput_rps: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    latency_p50_ms: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    latency_p95_ms: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    latency_p99_ms: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    error_rate: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    cpu_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    memory_mb: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
