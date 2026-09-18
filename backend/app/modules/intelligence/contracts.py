from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class MetricFeatures:
    concurrency: int
    throughput_rps: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    error_rate: float
    timeout_count: int
    cpu_percent: float
    memory_mb: float
    throughput_trend: float
    latency_p95_trend: float
    error_rate_trend: float


@dataclass(frozen=True, slots=True)
class RiskPredictionResult:
    probability: float
    predicted_degradation: bool
    model_version: str
    inference_latency_ms: int

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be between 0 and 1")
        if self.inference_latency_ms < 0:
            raise ValueError("inference_latency_ms must not be negative")


class RiskPredictor(Protocol):
    def predict_risk(self, features: MetricFeatures) -> RiskPredictionResult:
        """Return the local model prediction for one metric window."""
