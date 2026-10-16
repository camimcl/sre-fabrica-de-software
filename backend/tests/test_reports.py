import json
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.db.types import ControlStrategy, ExecutionStatus, UserRole
from app.main import app
from app.modules.auth.models import User
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.metrics.models import MetricWindow
from app.modules.projects.models import Endpoint, Project
from app.modules.reports.models import ComparisonReportExecution, ExecutionReport
from app.modules.reports.service import (
    create_comparison_report,
    generate_execution_report,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


@pytest.fixture
def api(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, sessionmaker]]:
    monkeypatch.setenv(
        "LOADFORGE_TOKEN_SECRET",
        "test-only-secret-value-with-at-least-32-bytes",
    )
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def session_override() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = session_override
    try:
        with TestClient(app) as client:
            yield client, factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _seed_experiment(db: Session) -> tuple[Project, User, list[TestExecution]]:
    user = User(
        full_name="QA Reports",
        email=f"qa-{uuid4()}@example.org",
        password_hash="x",
        role=UserRole.QA,
    )
    db.add(user)
    db.flush()
    project = Project(owner_id=user.id, name="Comparable project")
    db.add(project)
    db.flush()
    endpoint = Endpoint(
        project_id=project.id,
        name="Controlled target",
        base_url="http://127.0.0.1:9999",
        http_method="GET",
        authorization_confirmed=True,
        authorization_evidence="test",
    )
    db.add(endpoint)
    db.flush()

    executions: list[TestExecution] = []
    start = datetime.now(timezone.utc)
    strategy_factor = {
        ControlStrategy.FIXED: (40, 320, Decimal("0.08")),
        ControlStrategy.RULES: (45, 260, Decimal("0.05")),
        ControlStrategy.AI_HYBRID: (50, 220, Decimal("0.03")),
    }
    for strategy in ControlStrategy:
        scenario = TestScenario(
            project_id=project.id,
            endpoint_id=endpoint.id,
            created_by=user.id,
            name=f"Comparable {strategy.value}",
            duration_seconds=30,
            initial_concurrency=2,
            max_concurrency=20,
            ramp_up_per_window=2,
            timeout_ms=1000,
            strategy=strategy,
            p95_limit_ms=500,
            error_rate_limit=Decimal("0.10"),
        )
        db.add(scenario)
        db.flush()
        for repetition in range(3):
            execution = TestExecution(
                scenario_id=scenario.id,
                initiated_by=user.id,
                status=ExecutionStatus.COMPLETED,
                strategy=strategy,
                duration_seconds=30,
                initial_concurrency=2,
                max_concurrency=20,
                ramp_up_per_window=2,
                timeout_ms=1000,
                p95_limit_ms=500,
                error_rate_limit=Decimal("0.10"),
                authorization_acknowledged=True,
                started_at=start,
                ended_at=start + timedelta(seconds=30),
            )
            db.add(execution)
            db.flush()
            throughput, p95, error_rate = strategy_factor[strategy]
            for sequence in range(3):
                requests = throughput * 2 + repetition
                failures = round(requests * float(error_rate))
                db.add(
                    MetricWindow(
                        execution_id=execution.id,
                        sequence_number=sequence,
                        window_started_at=start + timedelta(seconds=sequence * 2),
                        window_duration_ms=2000,
                        concurrency=2 + sequence,
                        request_count=requests,
                        success_count=requests - failures,
                        timeout_count=failures,
                        throughput_rps=Decimal(str(throughput + repetition)),
                        latency_p50_ms=Decimal(str(p95 / 2)),
                        latency_p95_ms=Decimal(str(p95 + repetition)),
                        latency_p99_ms=Decimal(str(p95 + 50 + repetition)),
                        error_rate=error_rate,
                        cpu_percent=Decimal("10"),
                        memory_mb=Decimal("128"),
                    )
                )
            executions.append(execution)
    db.commit()
    return project, user, executions


def test_execution_report_aggregates_persisted_windows(db: Session) -> None:
    _, _, executions = _seed_experiment(db)
    execution = executions[0]
    report = generate_execution_report(db, execution)
    db.commit()

    assert report.total_requests > 0
    assert report.successful_requests <= report.total_requests
    summary = json.loads(report.summary)
    assert summary["window_count"] == 3
    assert summary["observed_duration_ms"] == 6000
    assert summary["peak_concurrency"] == 4


def test_comparison_requires_equivalent_repeated_strategies(db: Session) -> None:
    project, user, executions = _seed_experiment(db)
    with pytest.raises(HTTPException, match="at least 3"):
        create_comparison_report(
            db,
            project_id=project.id,
            created_by=user.id,
            name="Incomplete",
            execution_ids=[execution.id for execution in executions[:-1]],
        )

    executions[-1].duration_seconds = 31
    db.commit()
    with pytest.raises(HTTPException, match="equivalent"):
        create_comparison_report(
            db,
            project_id=project.id,
            created_by=user.id,
            name="Different conditions",
            execution_ids=[execution.id for execution in executions],
        )


def test_comparison_persists_strategy_statistics_and_deltas(db: Session) -> None:
    project, user, executions = _seed_experiment(db)
    comparison = create_comparison_report(
        db,
        project_id=project.id,
        created_by=user.id,
        name="Three strategies, three repetitions",
        execution_ids=[execution.id for execution in executions],
    )

    results = json.loads(comparison.results_json)
    assert comparison.repetitions_per_strategy == 3
    assert results["FIXED"]["runs"] == 3
    assert results["RULES"]["runs"] == 3
    assert results["AI_HYBRID"]["runs"] == 3
    assert results["AI_HYBRID"]["throughput_rps"]["mean"] > results["FIXED"]["throughput_rps"]["mean"]
    assert results["AI_HYBRID"]["latency_p95_ms"]["mean"] < results["RULES"]["latency_p95_ms"]["mean"]
    assert results["comparisons"]["AI_HYBRID_vs_FIXED"]["throughput_change_percent"] > 0
    assert len(
        list(
            db.scalars(
                select(ComparisonReportExecution).where(
                    ComparisonReportExecution.comparison_report_id == comparison.id
                )
            )
        )
    ) == 9
    assert len(list(db.scalars(select(ExecutionReport)))) == 9


def test_report_api_exposes_integrated_history_and_comparison(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, factory = api
    with factory() as db:
        project, user, executions = _seed_experiment(db)
        user.password_hash = hash_password("strong-password-123")
        db.commit()
        project_id = project.id
        execution_ids = [str(execution.id) for execution in executions]

    login = client.post(
        "/auth/login",
        json={"email": user.email, "password": "strong-password-123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = client.post(
        f"/projects/{project_id}/reports/comparisons",
        json={
            "name": "API comparison",
            "execution_ids": execution_ids,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    comparison = created.json()
    assert comparison["repetitions_per_strategy"] == 3
    assert len(comparison["execution_ids"]) == 9

    history = client.get(
        f"/projects/{project_id}/reports/executions", headers=headers
    )
    assert history.status_code == 200, history.text
    assert len(history.json()) == 9
    assert all(item["report"] is not None for item in history.json())

    detail = client.get(
        f"/projects/{project_id}/reports/comparisons/{comparison['id']}",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["conditions_fingerprint"] == comparison["conditions_fingerprint"]
