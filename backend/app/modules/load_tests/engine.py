"""Real load generation engine (Phase B).

Async HTTP traffic generation with windowed metric aggregation. Database
writes use the existing synchronous Session executed off the event loop via
``asyncio.to_thread`` (Option 1), keeping Phase A infrastructure intact.
"""

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.db.types import (
    ControlAction,
    ControlStrategy,
    ExecutionStatus,
    ModelStatus,
)
from app.modules.control.contracts import ControlInput, RulesController
from app.modules.control.models import ControlDecision
from app.modules.intelligence.contracts import RiskPredictor
from app.modules.intelligence.dataset import features_from_window
from app.modules.intelligence.models import ModelVersion, RiskPrediction
from app.modules.intelligence.predictor import SklearnRiskPredictor
from app.modules.load_tests.models import TestExecution
from app.modules.metrics.models import MetricWindow
from app.modules.projects.models import Endpoint


WINDOW_DURATION_MS = 2000


@dataclass(slots=True)
class RequestOutcome:
    latency_ms: float
    is_success: bool
    is_timeout: bool


@dataclass(slots=True)
class WindowAggregator:
    latencies: list[float] = field(default_factory=list)
    request_count: int = 0
    success_count: int = 0
    timeout_count: int = 0

    def add(self, outcome: RequestOutcome) -> None:
        self.request_count += 1
        self.latencies.append(outcome.latency_ms)
        if outcome.is_success:
            self.success_count += 1
        if outcome.is_timeout:
            self.timeout_count += 1

    def _percentile(self, pct: float) -> float:
        if not self.latencies:
            return 0.0
        ordered = sorted(self.latencies)
        # Nearest-rank method.
        rank = max(1, math.ceil(pct / 100 * len(ordered)))
        return ordered[rank - 1]

    def error_rate(self) -> Decimal:
        if self.request_count == 0:
            return Decimal("0")
        failures = self.request_count - self.success_count
        return round(Decimal(failures) / Decimal(self.request_count), 5)

    def throughput_rps(self, duration_ms: int) -> Decimal:
        if duration_ms <= 0:
            return Decimal("0")
        return round(Decimal(self.request_count) / (Decimal(duration_ms) / 1000), 4)

    def snapshot(
        self,
        *,
        execution_id: UUID,
        sequence_number: int,
        started_at: datetime,
        duration_ms: int,
        concurrency: int,
    ) -> dict:
        return {
            "execution_id": execution_id,
            "sequence_number": sequence_number,
            "window_started_at": started_at,
            "window_duration_ms": duration_ms,
            "concurrency": concurrency,
            "request_count": self.request_count,
            "success_count": self.success_count,
            "timeout_count": self.timeout_count,
            "throughput_rps": self.throughput_rps(duration_ms),
            "latency_p50_ms": round(Decimal(self._percentile(50)), 3),
            "latency_p95_ms": round(Decimal(self._percentile(95)), 3),
            "latency_p99_ms": round(Decimal(self._percentile(99)), 3),
            "error_rate": self.error_rate(),
            "cpu_percent": _local_cpu_percent(),
            "memory_mb": _local_memory_mb(),
        }


def _local_cpu_percent() -> Decimal:
    # Phase B (enxuta): target CPU is out of scope; use 0 as documented fallback.
    return Decimal("0")


def _local_memory_mb() -> Decimal:
    try:
        import resource  # POSIX only

        peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(Decimal(peak_kb) / 1024, 2)
    except Exception:
        return Decimal("0")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EngineRegistry:
    """Tracks at most one running load task per execution.

    Holds a strong reference to each background task so it is not garbage
    collected before completion.
    """

    def __init__(self) -> None:
        self._cancel_events: dict[UUID, asyncio.Event] = {}
        self._tasks: dict[UUID, asyncio.Task] = {}

    def register(self, execution_id: UUID) -> asyncio.Event:
        if execution_id in self._cancel_events:
            raise RuntimeError("Execution already running")
        event = asyncio.Event()
        self._cancel_events[execution_id] = event
        return event

    def track_task(self, execution_id: UUID, task: asyncio.Task) -> None:
        self._tasks[execution_id] = task

    def cancel(self, execution_id: UUID) -> bool:
        event = self._cancel_events.get(execution_id)
        if event is None:
            return False
        event.set()
        return True

    def finish(self, execution_id: UUID) -> None:
        self._cancel_events.pop(execution_id, None)
        self._tasks.pop(execution_id, None)

    def is_running(self, execution_id: UUID) -> bool:
        return execution_id in self._cancel_events


registry = EngineRegistry()


# --- Synchronous persistence helpers (run via asyncio.to_thread) ------------


def _load_plan(execution_id: UUID) -> dict | None:
    from app.modules.load_tests.models import TestScenario

    with Session(get_engine()) as db:
        execution = db.get(TestExecution, execution_id)
        if execution is None:
            return None
        scenario = db.get(TestScenario, execution.scenario_id)
        endpoint = (
            db.get(Endpoint, scenario.endpoint_id) if scenario is not None else None
        )
        return {
            "duration_seconds": execution.duration_seconds,
            "strategy": execution.strategy,
            "initial_concurrency": execution.initial_concurrency,
            "max_concurrency": execution.max_concurrency,
            "ramp_up_per_window": execution.ramp_up_per_window,
            "timeout_ms": execution.timeout_ms,
            "p95_limit_ms": execution.p95_limit_ms,
            "error_rate_limit": float(execution.error_rate_limit),
            "base_url": endpoint.base_url if endpoint else None,
            "http_method": endpoint.http_method if endpoint else "GET",
            "authorization_confirmed": (
                endpoint.authorization_confirmed if endpoint else False
            ),
        }


def _persist_window(values: dict) -> UUID:
    with Session(get_engine()) as db:
        window = MetricWindow(**values)
        db.add(window)
        db.commit()
        db.refresh(window)
        return window.id


def _load_approved_predictor(
    execution_id: UUID,
) -> tuple[UUID | None, RiskPredictor | None]:
    with Session(get_engine()) as db:
        execution = db.get(TestExecution, execution_id)
        if execution is None or execution.strategy != ControlStrategy.AI_HYBRID:
            return None, None
        model = db.scalar(
            select(ModelVersion)
            .where(ModelVersion.status == ModelStatus.APPROVED)
            .order_by(ModelVersion.created_at.desc())
        )
        if model is None:
            return None, None
        try:
            predictor = SklearnRiskPredictor(model)
        except Exception:
            return None, None
        execution.model_version_id = model.id
        db.commit()
        return model.id, predictor


def _evaluate_and_persist(
    *,
    execution_id: UUID,
    metric_window_id: UUID,
    predictor: RiskPredictor | None,
    model_version_id: UUID | None,
) -> int:
    with Session(get_engine()) as db:
        execution = db.get(TestExecution, execution_id)
        window = db.get(MetricWindow, metric_window_id)
        if execution is None or window is None:
            raise RuntimeError("Execution metric window was not found")
        previous = db.scalar(
            select(MetricWindow).where(
                MetricWindow.execution_id == execution_id,
                MetricWindow.sequence_number == window.sequence_number - 1,
            )
        )
        features = features_from_window(window, previous)
        prediction_row: RiskPrediction | None = None
        risk: float | None = None
        strategy = ControlStrategy.RULES
        fallback_reason: str | None = None

        if execution.strategy == ControlStrategy.AI_HYBRID:
            if predictor is None or model_version_id is None:
                fallback_reason = "Fallback por regras: nao ha modelo aprovado e valido. "
            else:
                try:
                    result = predictor.predict_risk(features)
                    risk = result.probability
                    prediction_row = RiskPrediction(
                        metric_window_id=window.id,
                        model_version_id=model_version_id,
                        risk_probability=Decimal(str(round(result.probability, 5))),
                        predicted_degradation=result.predicted_degradation,
                        inference_latency_ms=result.inference_latency_ms,
                    )
                    db.add(prediction_row)
                    db.flush()
                    strategy = ControlStrategy.AI_HYBRID
                except Exception:
                    fallback_reason = "Fallback por regras: a inferencia local falhou. "

        controller = RulesController(
            increase_step=max(1, execution.ramp_up_per_window)
        )
        result = controller.decide(
            ControlInput(
                concurrency=window.concurrency,
                max_concurrency=execution.max_concurrency,
                error_rate=float(window.error_rate),
                error_rate_limit=float(execution.error_rate_limit),
                p95_ms=float(window.latency_p95_ms),
                p95_limit_ms=float(execution.p95_limit_ms),
                risk=risk,
            )
        )
        decision = ControlDecision(
            metric_window_id=window.id,
            risk_prediction_id=prediction_row.id if prediction_row else None,
            strategy=strategy,
            action=ControlAction(result.action),
            previous_concurrency=result.previous_concurrency,
            next_concurrency=result.next_concurrency,
            reason=(fallback_reason or "") + result.reason,
        )
        db.add(decision)
        db.commit()
        return result.next_concurrency


def _finalize_execution(
    execution_id: UUID, status: ExecutionStatus, reason: str | None = None
) -> None:
    with Session(get_engine()) as db:
        execution = db.get(TestExecution, execution_id)
        if execution is None:
            return
        # Only the engine may move a RUNNING execution to a terminal state.
        # If it is no longer RUNNING, a concurrent path already finalized it;
        # do not overwrite that outcome.
        if execution.status != ExecutionStatus.RUNNING:
            return
        execution.status = status
        execution.ended_at = _now()
        if reason is not None:
            execution.cancellation_reason = reason
        db.commit()


# --- Core async loop --------------------------------------------------------


def _concurrency_for_window(plan: dict, window_index: int) -> int:
    level = plan["initial_concurrency"] + window_index * plan["ramp_up_per_window"]
    return min(level, plan["max_concurrency"])


async def _fire_one(
    client: httpx.AsyncClient, method: str, url: str
) -> RequestOutcome:
    loop = asyncio.get_event_loop()
    start = loop.time()
    try:
        # Streaming closes the response without retaining an arbitrarily large
        # body in memory. LoadForge measures response headers/status, not body
        # content, so buffering the payload would only increase resource use.
        async with client.stream(method, url) as response:
            latency_ms = (loop.time() - start) * 1000
            return RequestOutcome(
                latency_ms=latency_ms,
                is_success=response.status_code < 400,
                is_timeout=False,
            )
    except httpx.TimeoutException:
        latency_ms = (loop.time() - start) * 1000
        return RequestOutcome(latency_ms=latency_ms, is_success=False, is_timeout=True)
    except httpx.HTTPError:
        latency_ms = (loop.time() - start) * 1000
        return RequestOutcome(latency_ms=latency_ms, is_success=False, is_timeout=False)


async def run_execution(execution_id: UUID, cancel_event: asyncio.Event) -> None:
    """Drive one execution: fire load, aggregate windows, persist, finalize."""
    try:
        plan = await asyncio.to_thread(_load_plan, execution_id)
        if plan is None or not plan.get("base_url"):
            await asyncio.to_thread(
                _finalize_execution, execution_id, ExecutionStatus.FAILED
            )
            return
        if not plan["authorization_confirmed"]:
            await asyncio.to_thread(
                _finalize_execution, execution_id, ExecutionStatus.FAILED
            )
            return

        total_ms = plan["duration_seconds"] * 1000
        timeout_s = plan["timeout_ms"] / 1000
        cancelled = False
        model_version_id, predictor = await asyncio.to_thread(
            _load_approved_predictor, execution_id
        )
        current_concurrency = plan["initial_concurrency"]

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            elapsed_ms = 0
            window_index = 0
            while elapsed_ms < total_ms:
                if cancel_event.is_set():
                    cancelled = True
                    break
                # Last window uses only the remaining configured time.
                window_ms = min(WINDOW_DURATION_MS, total_ms - elapsed_ms)
                concurrency = (
                    _concurrency_for_window(plan, window_index)
                    if plan["strategy"] == ControlStrategy.FIXED
                    else current_concurrency
                )
                aggregator = WindowAggregator()
                window_started = _now()
                loop = asyncio.get_running_loop()
                window_clock_started = loop.time()
                await _run_window(
                    client=client,
                    method=plan["http_method"],
                    url=str(plan["base_url"]),
                    concurrency=concurrency,
                    window_seconds=window_ms / 1000,
                    aggregator=aggregator,
                    cancel_event=cancel_event,
                )
                observed_window_ms = max(
                    1, min(window_ms, round((loop.time() - window_clock_started) * 1000))
                )
                snapshot = aggregator.snapshot(
                    execution_id=execution_id,
                    sequence_number=window_index,
                    started_at=window_started,
                    duration_ms=observed_window_ms,
                    concurrency=concurrency,
                )
                metric_window_id = await asyncio.to_thread(_persist_window, snapshot)
                if plan["strategy"] != ControlStrategy.FIXED:
                    current_concurrency = await asyncio.to_thread(
                        _evaluate_and_persist,
                        execution_id=execution_id,
                        metric_window_id=metric_window_id,
                        predictor=predictor,
                        model_version_id=model_version_id,
                    )
                elapsed_ms += window_ms
                window_index += 1
                if cancel_event.is_set():
                    cancelled = True
                    break

        if cancelled:
            await asyncio.to_thread(
                _finalize_execution,
                execution_id,
                ExecutionStatus.CANCELLED,
            )
        else:
            await asyncio.to_thread(
                _finalize_execution, execution_id, ExecutionStatus.COMPLETED
            )
    except Exception:
        await asyncio.to_thread(
            _finalize_execution, execution_id, ExecutionStatus.FAILED
        )
    finally:
        registry.finish(execution_id)


async def _run_window(
    *,
    client: httpx.AsyncClient,
    method: str,
    url: str,
    concurrency: int,
    window_seconds: float,
    aggregator: WindowAggregator,
    cancel_event: asyncio.Event,
) -> None:
    """Keep `concurrency` requests in flight until the window elapses."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + window_seconds
    async def worker() -> None:
        while loop.time() < deadline and not cancel_event.is_set():
            outcome = await _fire_one(client, method, url)
            aggregator.add(outcome)

    # One long-lived worker per configured concurrent slot avoids the previous
    # ramp-up race in which only one request was often active against fast
    # targets. In-flight calls are drained when the window or stop signal ends.
    workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
    await asyncio.gather(*workers, return_exceptions=True)
