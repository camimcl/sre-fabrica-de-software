from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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
