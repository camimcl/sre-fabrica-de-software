from datetime import datetime
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import ControlAction, ControlStrategy


class ControlDecision(Base):
    __tablename__ = "control_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    metric_window_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_windows.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    risk_prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risk_predictions.id", ondelete="SET NULL"),
        unique=True,
    )
    strategy: Mapped[ControlStrategy] = mapped_column(
        Enum(ControlStrategy, name="control_strategy"), nullable=False
    )
    action: Mapped[ControlAction] = mapped_column(
        Enum(ControlAction, name="control_action"), nullable=False
    )
    previous_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    next_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
