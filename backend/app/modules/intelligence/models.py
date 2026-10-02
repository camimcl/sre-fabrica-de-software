from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import ModelStatus


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (Index('uq_model_single_approved', 'status', unique=True,
        postgresql_where=text("status = 'APPROVED'"), sqlite_where=text("status = 'APPROVED'")),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    algorithm: Mapped[str] = mapped_column(String(80), nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus, name="model_status"), nullable=False
    )
    precision_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 5))
    recall_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 5))
    f1_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 5))
    accuracy_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 5))
    training_sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    training_dataset_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    metric_window_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_windows.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    risk_probability: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    predicted_degradation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    inference_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
