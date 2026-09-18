from dataclasses import dataclass
import math
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ControlInput:
    concurrency: int
    max_concurrency: int
    error_rate: float
    error_rate_limit: float
    p95_ms: float
    p95_limit_ms: float
    risk: float | None

    def __post_init__(self) -> None:
        if self.concurrency <= 0:
            raise ValueError("concurrency must be positive")
        if self.max_concurrency < self.concurrency:
            raise ValueError("max_concurrency must not be lower than concurrency")
        if not 0.0 <= self.error_rate <= 1.0:
            raise ValueError("error_rate must be between 0 and 1")
        if not 0.0 <= self.error_rate_limit <= 1.0:
            raise ValueError("error_rate_limit must be between 0 and 1")
        if self.p95_limit_ms <= 0:
            raise ValueError("p95_limit_ms must be positive")
        if self.risk is not None and not 0.0 <= self.risk <= 1.0:
            raise ValueError("risk must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ControlDecisionResult:
    action: str
    previous_concurrency: int
    next_concurrency: int
    reason: str


class ConcurrencyController(Protocol):
    def decide(self, control_input: ControlInput) -> ControlDecisionResult:
        """Return a decision without mutating execution state."""


class RulesController:
    """Deterministic fallback used when the local model is unavailable."""

    def __init__(
        self,
        *,
        decrease_factor: float = 0.75,
        increase_step: int = 1,
        caution_ratio: float = 0.80,
    ) -> None:
        if not 0.0 < decrease_factor < 1.0:
            raise ValueError("decrease_factor must be between 0 and 1")
        if increase_step <= 0:
            raise ValueError("increase_step must be positive")
        if not 0.0 < caution_ratio < 1.0:
            raise ValueError("caution_ratio must be between 0 and 1")
        self._decrease_factor = decrease_factor
        self._increase_step = increase_step
        self._caution_ratio = caution_ratio

    def decide(self, control_input: ControlInput) -> ControlDecisionResult:
        risk_high = control_input.risk is not None and control_input.risk >= 0.70
        limits_violated = (
            control_input.error_rate >= control_input.error_rate_limit
            or control_input.p95_ms >= control_input.p95_limit_ms
        )
        if risk_high or limits_violated:
            next_concurrency = max(
                1, math.floor(control_input.concurrency * self._decrease_factor)
            )
            return ControlDecisionResult(
                action="DECREASE",
                previous_concurrency=control_input.concurrency,
                next_concurrency=next_concurrency,
                reason="Risco alto ou limite observado excedido.",
            )

        risk_intermediate = (
            control_input.risk is not None and control_input.risk >= 0.40
        )
        close_to_limit = (
            control_input.error_rate
            >= control_input.error_rate_limit * self._caution_ratio
            or control_input.p95_ms
            >= control_input.p95_limit_ms * self._caution_ratio
        )
        if risk_intermediate or close_to_limit:
            return ControlDecisionResult(
                action="HOLD",
                previous_concurrency=control_input.concurrency,
                next_concurrency=control_input.concurrency,
                reason="Risco intermediário ou métrica próxima do limite.",
            )

        next_concurrency = min(
            control_input.max_concurrency,
            control_input.concurrency + self._increase_step,
        )
        action = "INCREASE" if next_concurrency > control_input.concurrency else "HOLD"
        reason = (
            "Métricas estáveis dentro dos limites."
            if action == "INCREASE"
            else "Concorrência máxima já atingida."
        )
        return ControlDecisionResult(
            action=action,
            previous_concurrency=control_input.concurrency,
            next_concurrency=next_concurrency,
            reason=reason,
        )
