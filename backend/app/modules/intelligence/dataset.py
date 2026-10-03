"""Feature engineering and temporal labels for the local risk model."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.types import ExecutionStatus

from app.modules.intelligence.contracts import MetricFeatures
from app.modules.load_tests.models import TestExecution
from app.modules.metrics.models import MetricWindow


FEATURE_NAMES = tuple(MetricFeatures.__dataclass_fields__)
MIN_TRAINING_SAMPLES = 20
PREDICTION_HORIZON_WINDOWS = 5


@dataclass(frozen=True, slots=True)
class TrainingSample:
    features: MetricFeatures
    degraded_within_horizon: bool
    execution_id: str
    sequence_number: int
    observed_at: datetime
    label_ends_at: datetime


def features_from_window(
    window: MetricWindow, previous: MetricWindow | None
) -> MetricFeatures:
    def trend(current: float, prior: float) -> float:
        if prior == 0:
            return 0.0 if current == 0 else 1.0
        return (current - prior) / abs(prior)

    return MetricFeatures(
        concurrency=window.concurrency,
        throughput_rps=float(window.throughput_rps),
        latency_p50_ms=float(window.latency_p50_ms),
        latency_p95_ms=float(window.latency_p95_ms),
        latency_p99_ms=float(window.latency_p99_ms),
        error_rate=float(window.error_rate),
        timeout_count=window.timeout_count,
        cpu_percent=float(window.cpu_percent),
        memory_mb=float(window.memory_mb),
        throughput_trend=trend(
            float(window.throughput_rps),
            float(previous.throughput_rps) if previous else 0.0,
        ),
        latency_p95_trend=trend(
            float(window.latency_p95_ms),
            float(previous.latency_p95_ms) if previous else 0.0,
        ),
        error_rate_trend=trend(
            float(window.error_rate),
            float(previous.error_rate) if previous else 0.0,
        ),
    )


def feature_vector(features: MetricFeatures) -> list[float]:
    return [float(getattr(features, name)) for name in FEATURE_NAMES]


def _is_degraded(next_window: MetricWindow, execution: TestExecution) -> bool:
    return (
        float(next_window.latency_p95_ms) >= execution.p95_limit_ms
        or float(next_window.error_rate) >= float(execution.error_rate_limit)
    )


def _observation_end(window: MetricWindow) -> datetime:
    started = window.window_started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return started.astimezone(timezone.utc) + timedelta(milliseconds=window.window_duration_ms)


def build_training_samples(db: Session) -> list[TrainingSample]:
    executions = list(
        db.scalars(
            select(TestExecution).where(TestExecution.status == ExecutionStatus.COMPLETED).order_by(
                TestExecution.created_at, TestExecution.id
            )
        )
    )
    samples: list[TrainingSample] = []
    for execution in executions:
        windows = list(
            db.scalars(
                select(MetricWindow)
                .where(MetricWindow.execution_id == execution.id)
                .order_by(MetricWindow.sequence_number)
            )
        )
        for index in range(len(windows) - PREDICTION_HORIZON_WINDOWS):
            current = windows[index]
            future = windows[
                index + 1 : index + 1 + PREDICTION_HORIZON_WINDOWS
            ]
            if any(w.window_duration_ms < 1900 or w.request_count == 0 for w in [current, *future]):
                continue
            if any(b.sequence_number != a.sequence_number + 1 for a, b in zip([current, *future], future)):
                continue
            samples.append(
                TrainingSample(
                    features=features_from_window(
                        current, windows[index - 1] if index else None
                    ),
                    degraded_within_horizon=any(
                        _is_degraded(candidate, execution) for candidate in future
                    ),
                    execution_id=str(execution.id),
                    sequence_number=current.sequence_number,
                    observed_at=_observation_end(current),
                    label_ends_at=_observation_end(future[-1]),
                )
            )
    return sorted(samples, key=lambda sample: (sample.observed_at, sample.execution_id, sample.sequence_number))


def dataset_sha256(samples: list[TrainingSample]) -> str:
    canonical = [
        {
            "features": asdict(sample.features),
            "label": sample.degraded_within_horizon,
            "execution_id": sample.execution_id,
            "sequence_number": sample.sequence_number,
            "observed_at": sample.observed_at.isoformat(),
            "label_ends_at": sample.label_ends_at.isoformat(),
        }
        for sample in samples
    ]
    encoded = json.dumps(
        canonical, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
