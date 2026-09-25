"""Phase B: load generation engine tests against a local HTTP target.

No external network is used. A deterministic HTTP server runs on an ephemeral
localhost port. The engine's synchronous persistence uses a shared in-memory
SQLite engine, injected by monkeypatching get_engine in the engine module.
"""

import asyncio
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.types import ControlStrategy, ExecutionStatus, UserRole
from app.modules.auth.models import User
from app.modules.load_tests import engine as load_engine
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.metrics.models import MetricWindow
from app.modules.projects.models import Endpoint, Project


class _Handler(BaseHTTPRequestHandler):
    status_code = 200
    delay_seconds = 0.0

    def do_GET(self):  # noqa: N802
        if _Handler.delay_seconds:
            time.sleep(_Handler.delay_seconds)
        self.send_response(_Handler.status_code)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # silence
        return


@pytest.fixture
def target() -> Iterator[str]:
    _Handler.status_code = 200
    _Handler.delay_seconds = 0.0
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def db_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(load_engine, "get_engine", lambda: engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def _seed(factory: sessionmaker, base_url: str, **scenario_over) -> uuid4:
    with factory() as db:
        user = User(
            full_name="QA",
            email=f"qa-{uuid4()}@example.org",
            password_hash="x",
            role=UserRole.QA,
        )
        db.add(user)
        db.flush()
        project = Project(owner_id=user.id, name="P")
        db.add(project)
        db.flush()
        endpoint = Endpoint(
            project_id=project.id,
            name="target",
            base_url=base_url,
            http_method="GET",
            authorization_confirmed=True,
            authorization_evidence="ok",
        )
        db.add(endpoint)
        db.flush()
        scenario_fields = {
            "duration_seconds": 2,
            "initial_concurrency": 2,
            "max_concurrency": 4,
            "ramp_up_per_window": 1,
            "timeout_ms": 1000,
            "p95_limit_ms": 800,
            "error_rate_limit": "0.5",
        }
        scenario_fields.update(scenario_over)
        scenario = TestScenario(
            project_id=project.id,
            endpoint_id=endpoint.id,
            created_by=user.id,
            name="S",
            strategy=ControlStrategy.RULES,
            **scenario_fields,
        )
        db.add(scenario)
        db.flush()
        execution = TestExecution(
            scenario_id=scenario.id,
            initiated_by=user.id,
            status=ExecutionStatus.RUNNING,
            strategy=ControlStrategy.RULES,
            duration_seconds=scenario.duration_seconds,
            initial_concurrency=scenario.initial_concurrency,
            max_concurrency=scenario.max_concurrency,
            timeout_ms=scenario.timeout_ms,
            p95_limit_ms=scenario.p95_limit_ms,
            error_rate_limit=scenario.error_rate_limit,
            authorization_acknowledged=True,
        )
        db.add(execution)
        db.commit()
        return execution.id


def _windows(factory: sessionmaker, execution_id) -> list[MetricWindow]:
    with factory() as db:
        return list(
            db.scalars(
                select(MetricWindow)
                .where(MetricWindow.execution_id == execution_id)
                .order_by(MetricWindow.sequence_number)
            )
        )


def _status(factory: sessionmaker, execution_id) -> ExecutionStatus:
    with factory() as db:
        return db.get(TestExecution, execution_id).status


def test_engine_completes_and_records_windows(db_engine, target) -> None:
    execution_id = _seed(db_engine, target)
    event = asyncio.Event()
    asyncio.run(load_engine.run_execution(execution_id, event))

    assert _status(db_engine, execution_id) == ExecutionStatus.COMPLETED
    windows = _windows(db_engine, execution_id)
    assert len(windows) >= 1
    first = windows[0]
    assert first.request_count > 0
    assert first.success_count == first.request_count  # target returns 200
    assert 0 <= float(first.error_rate) <= 1


def test_engine_counts_errors(db_engine, target, monkeypatch) -> None:
    monkeypatch.setattr(_Handler, "status_code", 500)
    execution_id = _seed(db_engine, target)
    asyncio.run(load_engine.run_execution(execution_id, asyncio.Event()))

    windows = _windows(db_engine, execution_id)
    assert windows
    # every response is a 500 -> failures, error_rate should be high
    assert float(windows[0].error_rate) > 0.5


def test_engine_counts_timeouts(db_engine, target, monkeypatch) -> None:
    monkeypatch.setattr(_Handler, "delay_seconds", 0.3)
    execution_id = _seed(db_engine, target, timeout_ms=50)
    asyncio.run(load_engine.run_execution(execution_id, asyncio.Event()))

    windows = _windows(db_engine, execution_id)
    assert windows
    assert windows[0].timeout_count > 0


def test_engine_respects_max_concurrency(db_engine, target) -> None:
    execution_id = _seed(
        db_engine, target, initial_concurrency=3, max_concurrency=3, ramp_up_per_window=5
    )
    asyncio.run(load_engine.run_execution(execution_id, asyncio.Event()))
    windows = _windows(db_engine, execution_id)
    assert all(w.concurrency <= 3 for w in windows)


def test_engine_cancellation_is_effective(db_engine, target, monkeypatch) -> None:
    monkeypatch.setattr(_Handler, "delay_seconds", 0.05)
    execution_id = _seed(db_engine, target, duration_seconds=30)
    event = asyncio.Event()

    async def drive() -> None:
        task = asyncio.create_task(load_engine.run_execution(execution_id, event))
        await asyncio.sleep(0.2)
        event.set()  # emergency stop
        await asyncio.wait_for(task, timeout=10)

    asyncio.run(drive())
    assert _status(db_engine, execution_id) == ExecutionStatus.CANCELLED


def test_engine_fails_on_unauthorized_endpoint(db_engine, target) -> None:
    execution_id = _seed(db_engine, target)
    # flip the endpoint to unauthorized
    with db_engine() as db:
        execution = db.get(TestExecution, execution_id)
        scenario = db.get(TestScenario, execution.scenario_id)
        endpoint = db.get(Endpoint, scenario.endpoint_id)
        endpoint.authorization_confirmed = False
        db.commit()

    asyncio.run(load_engine.run_execution(execution_id, asyncio.Event()))
    assert _status(db_engine, execution_id) == ExecutionStatus.FAILED


def test_aggregator_math() -> None:
    agg = load_engine.WindowAggregator()
    agg.add(load_engine.RequestOutcome(latency_ms=10, is_success=True, is_timeout=False))
    agg.add(load_engine.RequestOutcome(latency_ms=20, is_success=False, is_timeout=True))
    assert agg.request_count == 2
    assert agg.success_count == 1
    assert agg.timeout_count == 1
    assert float(agg.error_rate()) == 0.5
