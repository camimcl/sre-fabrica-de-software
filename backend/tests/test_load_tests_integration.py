"""Full integration: API + load engine + persistence.

Exercises the real flow through the HTTP API with the engine ENABLED and a
local deterministic HTTP target. Runs against SQLite by default and against
PostgreSQL when LOADFORGE_TEST_DATABASE_URL is set (marked `integration`).
"""

import os
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db, get_engine
from app.db.types import UserRole
from app.main import app
from app.modules.auth.models import User
from app.modules.load_tests import engine as load_engine
from app.modules.metrics.models import MetricWindow


class _Handler(BaseHTTPRequestHandler):
    status_code = 200

    def do_GET(self):  # noqa: N802
        self.send_response(_Handler.status_code)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        return


@pytest.fixture
def target() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _, port = server.server_address
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, sessionmaker]]:
    monkeypatch.setenv(
        "LOADFORGE_TOKEN_SECRET", "test-only-secret-value-with-at-least-32-bytes"
    )
    db_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(db_engine)
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)

    def session_override() -> Iterator[Session]:
        with factory() as db:
            yield db

    # Engine stays ENABLED to exercise the real integrated flow. The engine's
    # background persistence resolves its own engine via load_engine.get_engine;
    # point it at the same in-memory database the API uses.
    monkeypatch.setattr(load_engine, "get_engine", lambda: db_engine)
    app.dependency_overrides[get_db] = session_override
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    db_engine.dispose()


def _bootstrap(client: TestClient, factory: sessionmaker, base_url: str) -> dict:
    with factory() as db:
        qa = User(
            full_name="QA",
            email="qa-int@example.org",
            password_hash=hash_password("strong-password-123"),
            role=UserRole.QA,
        )
        db.add(qa)
        db.commit()
    headers = {
        "Authorization": "Bearer "
        + client.post(
            "/auth/login",
            json={"email": "qa-int@example.org", "password": "strong-password-123"},
        ).json()["access_token"]
    }
    project_id = client.post(
        "/projects", json={"name": "Int"}, headers=headers
    ).json()["id"]
    endpoint_id = client.post(
        f"/projects/{project_id}/endpoints",
        json={
            "name": "T",
            "base_url": base_url,
            "http_method": "GET",
            "authorization_confirmed": True,
            "authorization_evidence": "ok",
        },
        headers=headers,
    ).json()["id"]
    scenario_id = client.post(
        f"/projects/{project_id}/scenarios",
        json={
            "name": "S",
            "endpoint_id": endpoint_id,
            "duration_seconds": 1,
            "initial_concurrency": 2,
            "max_concurrency": 4,
            "ramp_up_per_window": 0,
            "timeout_ms": 1000,
            "strategy": "RULES",
            "p95_limit_ms": 800,
            "error_rate_limit": "0.5",
        },
        headers=headers,
    ).json()["id"]
    return {
        "headers": headers,
        "project_id": project_id,
        "endpoint_id": endpoint_id,
        "scenario_id": scenario_id,
    }


def _create_execution(client: TestClient, ctx: dict) -> str:
    return client.post(
        f"/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}/executions",
        json={"authorization_acknowledged": True},
        headers=ctx["headers"],
    ).json()["id"]


def _wait_terminal(client: TestClient, ctx: dict, execution_id: str, timeout=15):
    base = (
        f"/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}"
        f"/executions/{execution_id}"
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(base, headers=ctx["headers"]).json()["status"]
        if status in {"COMPLETED", "CANCELLED", "FAILED"}:
            return status
        time.sleep(0.2)
    return client.get(base, headers=ctx["headers"]).json()["status"]


def test_start_runs_engine_and_persists_metrics(api, target) -> None:
    client, factory = api
    ctx = _bootstrap(client, factory, target)
    execution_id = _create_execution(client, ctx)
    base = (
        f"/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}"
        f"/executions/{execution_id}"
    )
    started = client.post(f"{base}/start", headers=ctx["headers"])
    assert started.status_code == 200
    assert started.json()["status"] == "RUNNING"

    assert _wait_terminal(client, ctx, execution_id) == "COMPLETED"

    windows = client.get(f"{base}/metric-windows", headers=ctx["headers"]).json()
    assert len(windows) >= 1
    assert windows[0]["request_count"] > 0


def test_non_multiple_duration_records_actual_window(api, target) -> None:
    client, factory = api
    ctx = _bootstrap(client, factory, target)
    # duration 1s with 2s windows -> a single window of 1000ms
    execution_id = _create_execution(client, ctx)
    base = (
        f"/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}"
        f"/executions/{execution_id}"
    )
    client.post(f"{base}/start", headers=ctx["headers"])
    assert _wait_terminal(client, ctx, execution_id) == "COMPLETED"
    windows = client.get(f"{base}/metric-windows", headers=ctx["headers"]).json()
    assert len(windows) == 1
    assert windows[0]["window_duration_ms"] == 1000


def test_manual_complete_blocked_while_engine_active(api, target) -> None:
    client, factory = api
    ctx = _bootstrap(client, factory, target)
    execution_id = _create_execution(client, ctx)
    base = (
        f"/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}"
        f"/executions/{execution_id}"
    )
    client.post(f"{base}/start", headers=ctx["headers"])
    # Immediately try to complete manually while the engine is running.
    blocked = client.post(f"{base}/complete", headers=ctx["headers"])
    assert blocked.status_code == 409
    _wait_terminal(client, ctx, execution_id)


def test_start_blocked_when_authorization_revoked(api, target) -> None:
    client, factory = api
    ctx = _bootstrap(client, factory, target)
    execution_id = _create_execution(client, ctx)
    # Revoke the endpoint authorization after creation.
    from uuid import UUID

    from app.modules.projects.models import Endpoint

    with factory() as db:
        endpoint = db.get(Endpoint, UUID(ctx["endpoint_id"]))
        endpoint.authorization_confirmed = False
        db.commit()

    base = (
        f"/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}"
        f"/executions/{execution_id}"
    )
    blocked = client.post(f"{base}/start", headers=ctx["headers"])
    assert blocked.status_code == 409
    assert "authorization" in blocked.json()["detail"].lower()
    assert client.get(base, headers=ctx["headers"]).json()["status"] == "PENDING"


def test_ramp_up_zero_accepted_by_api_and_db(api, target) -> None:
    client, factory = api
    ctx = _bootstrap(client, factory, target)
    # The bootstrap scenario already uses ramp_up_per_window=0 and was created
    # (201) above; confirm it persisted.
    scenario = client.get(
        f"/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}",
        headers=ctx["headers"],
    )
    assert scenario.status_code == 200
    assert scenario.json()["ramp_up_per_window"] == 0


# --- PostgreSQL integration -------------------------------------------------


@pytest.mark.integration
def test_full_flow_on_postgres(monkeypatch: pytest.MonkeyPatch, target) -> None:
    database_url = os.getenv("LOADFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("LOADFORGE_TEST_DATABASE_URL is not set")
    if not (make_url(database_url).database or "").endswith("_test"):
        pytest.fail("Integration tests require a database ending in _test")

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv(
        "LOADFORGE_TOKEN_SECRET", "integration-test-secret-with-at-least-32-bytes"
    )
    get_engine.cache_clear()
    pg_engine = create_engine(database_url, pool_pre_ping=True)
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    # Point the load engine's synchronous persistence at the same PostgreSQL.
    monkeypatch.setattr(load_engine, "get_engine", lambda: pg_engine)

    def session_override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = session_override
    created = {}
    try:
        with TestClient(app) as client:
            ctx = _bootstrap(client, factory, target)
            created = ctx
            execution_id = _create_execution(client, ctx)
            base = (
                f"/projects/{ctx['project_id']}/scenarios/{ctx['scenario_id']}"
                f"/executions/{execution_id}"
            )
            assert client.post(f"{base}/start", headers=ctx["headers"]).status_code == 200
            assert _wait_terminal(client, ctx, execution_id) == "COMPLETED"

            # Metrics persisted in PostgreSQL and retrievable via a fresh session.
            with factory() as db:
                from uuid import UUID

                windows = list(
                    db.scalars(
                        select(MetricWindow).where(
                            MetricWindow.execution_id == UUID(execution_id)
                        )
                    )
                )
                assert len(windows) >= 1
    finally:
        app.dependency_overrides.clear()
        _cleanup_postgres(factory, created)
        pg_engine.dispose()
        get_engine.cache_clear()


def _cleanup_postgres(factory: sessionmaker, ctx: dict) -> None:
    if not ctx:
        return
    from uuid import UUID

    from app.modules.load_tests.models import TestExecution, TestScenario
    from app.modules.projects.models import Endpoint, Project

    with factory() as db:
        scenario_id = UUID(ctx["scenario_id"])
        for execution in db.scalars(
            select(TestExecution).where(TestExecution.scenario_id == scenario_id)
        ):
            db.query(MetricWindow).filter(
                MetricWindow.execution_id == execution.id
            ).delete()
            db.delete(execution)
        db.query(TestScenario).filter(TestScenario.id == scenario_id).delete()
        db.query(Endpoint).filter(Endpoint.id == UUID(ctx["endpoint_id"])).delete()
        db.query(Project).filter(Project.id == UUID(ctx["project_id"])).delete()
        db.query(User).filter(User.email == "qa-int@example.org").delete()
        db.commit()
