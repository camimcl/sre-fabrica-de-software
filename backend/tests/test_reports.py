import json
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import models  # noqa: F401
from app.db import session as db_session
from app.db.base import Base
from app.db.session import get_db
from app.db.types import ControlStrategy, ExecutionStatus, UserRole
from app.main import app
from app.modules.auth.models import User
from app.modules.load_tests.access import require_execution, require_scenario
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.metrics.models import MetricWindow
from app.modules.projects.access import require_owned_project, require_project
from app.modules.projects.models import Endpoint, Project
from app.modules.reports import service as report_service
from app.modules.reports.models import ComparisonReport, ComparisonReportExecution, ExecutionReport
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
                target_snapshot=json.dumps({
                    "endpoint_id": str(endpoint.id),
                    "base_url": endpoint.base_url,
                    "http_method": endpoint.http_method,
                    "window_duration_ms": 2000,
                }),
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


def test_shared_access_contract_returns_scoped_resources(db: Session, monkeypatch) -> None:
    project, user, executions = _seed_experiment(db)
    execution = executions[0]

    def reject_commit():
        pytest.fail("Access lookups must not commit")

    monkeypatch.setattr(db, "commit", reject_commit)
    assert require_project(db, project.id) is project
    assert require_owned_project(db, project.id, user) is project
    assert require_scenario(db, project.id, execution.scenario_id).id == execution.scenario_id
    assert require_execution(db, execution.scenario_id, execution.id) is execution
    assert not db.new and not db.dirty and not db.deleted


def test_shared_access_contract_preserves_not_found_and_owner_errors(db: Session) -> None:
    project, user, executions = _seed_experiment(db)
    execution = executions[0]
    other_project, other_user, other_executions = _seed_experiment(db)
    cases = [
        (require_project, (db, uuid4()), 404, "Project not found"),
        (require_owned_project, (db, uuid4(), user), 404, "Project not found"),
        (require_owned_project, (db, project.id, other_user), 403, "Project owner required"),
        (require_scenario, (db, project.id, uuid4()), 404, "Scenario not found"),
        (require_scenario, (db, other_project.id, execution.scenario_id), 404, "Scenario not found"),
        (require_execution, (db, execution.scenario_id, uuid4()), 404, "Execution not found"),
        (require_execution, (db, other_executions[0].scenario_id, execution.id), 404, "Execution not found"),
    ]
    for lookup, args, status, detail in cases:
        with pytest.raises(HTTPException) as error:
            lookup(*args)
        assert error.value.status_code == status
        assert error.value.detail == detail


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
    assert results["ai_evidence"]["unverified_windows"] == 9
    assert results["ai_evidence"]["inference_windows"] == 0
    assert [warning["code"] for warning in results["warnings"]] == [
        "AI_INFERENCE_UNVERIFIED", "MODEL_VERSION_UNVERIFIED",
    ]
    assert all(
        f" WARNING: {warning['message']}" in comparison.conclusion
        for warning in results["warnings"]
    )
    assert "cannot be attributed exclusively" in comparison.conclusion
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
    assert [warning["code"] for warning in comparison["results"]["warnings"]] == [
        "AI_INFERENCE_UNVERIFIED", "MODEL_VERSION_UNVERIFIED",
    ]

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
    assert detail.json()["results"]["warnings"] == comparison["results"]["warnings"]
    path = f"/projects/{project_id}/reports/comparisons"
    payload = {"name": "Another", "execution_ids": execution_ids}
    assert client.post(path, json=payload).status_code == 401
    assert client.post(path, json={**payload, "name": "   "}, headers=headers).status_code == 422
    assert client.post(path, json={**payload, "execution_ids": [execution_ids[0]] * 9}, headers=headers).status_code == 422
    assert client.post(path, json={**payload, "execution_ids": execution_ids[:-1] + [str(uuid4())]}, headers=headers).status_code == 404
    with factory() as db:
        viewer = db.get(User, user.id)
        viewer.role = UserRole.VIEWER
        db.commit()
    assert client.post(path, json=payload, headers=headers).status_code == 403
    assert client.get(path, headers=headers).status_code == 200


@pytest.mark.parametrize("preexisting_report", [False, True])
def test_aborted_comparison_does_not_persist_partial_execution_reports(
    api: tuple[TestClient, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
    preexisting_report: bool,
) -> None:
    client, factory = api
    # Exercise the production dependency's transaction cleanup, not a test rollback.
    app.dependency_overrides.pop(get_db)
    monkeypatch.setattr(db_session, "get_engine", lambda: factory.kw["bind"])
    with factory() as db:
        project, user, executions = _seed_experiment(db)
        user.password_hash = hash_password("strong-password-123")
        if preexisting_report:
            existing = generate_execution_report(db, executions[0])
            # Recalculation changes this stale value; that update must roll back too.
            existing.total_requests = 1
        missing_windows_id = next(
            execution.id for execution in executions
            if execution.strategy == ControlStrategy.RULES
        )
        db.execute(delete(MetricWindow).where(
            MetricWindow.execution_id == missing_windows_id
        ))
        db.commit()
        project_id, email = project.id, user.email
        execution_ids = [str(execution.id) for execution in executions]
        baseline_reports = list(db.execute(select(ExecutionReport.__table__)).mappings())
        baseline_window_ids = set(db.scalars(select(MetricWindow.id)))

    flushed_execution_ids = set()

    def observe_generation(db: Session, execution: TestExecution) -> ExecutionReport:
        if execution.id == missing_windows_id:
            # FIXED is processed before RULES, so failure really occurs mid-loop.
            assert len(flushed_execution_ids) >= 3
            visible_ids = set(db.scalars(select(ExecutionReport.execution_id)))
            assert flushed_execution_ids <= visible_ids
            assert len(visible_ids) > len(baseline_reports)
        report = generate_execution_report(db, execution)
        flushed_execution_ids.add(execution.id)
        return report

    monkeypatch.setattr(report_service, "generate_execution_report", observe_generation)
    login = client.post(
        "/auth/login", json={"email": email, "password": "strong-password-123"},
    )
    assert login.status_code == 200, login.text
    response = client.post(
        f"/projects/{project_id}/reports/comparisons",
        json={"name": "Aborted comparison", "execution_ids": execution_ids},
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Execution has no metric windows to report"
    assert len(flushed_execution_ids) >= 3

    # The request has ended; inspect durable state through a separate session.
    with factory() as reopened:
        assert list(reopened.execute(select(ExecutionReport.__table__)).mappings()) == baseline_reports
        assert list(reopened.scalars(select(ComparisonReport.id))) == []
        assert list(reopened.scalars(select(ComparisonReportExecution.id))) == []
        assert set(reopened.scalars(select(MetricWindow.id))) == baseline_window_ids
        assert {str(value) for value in reopened.scalars(select(TestExecution.id))} == set(execution_ids)


def test_comparison_uses_recorded_target_not_mutable_endpoint(db: Session) -> None:
    project, user, executions = _seed_experiment(db)
    endpoint = db.scalar(select(Endpoint).where(Endpoint.project_id == project.id))
    endpoint.base_url = "http://127.0.0.1:9998/changed"
    db.commit()
    comparison = create_comparison_report(
        db, project_id=project.id, created_by=user.id, name="Original target",
        execution_ids=[execution.id for execution in executions],
    )
    assert json.loads(comparison.conditions_json)["target"]["base_url"] == "http://127.0.0.1:9999"
    target = json.loads(executions[-1].target_snapshot)
    target["base_url"] = endpoint.base_url
    executions[-1].target_snapshot = json.dumps(target)
    db.commit()
    with pytest.raises(HTTPException, match="equivalent"):
        create_comparison_report(
            db, project_id=project.id, created_by=user.id, name="Changed target",
            execution_ids=[execution.id for execution in executions],
        )


@pytest.mark.parametrize("snapshot", [None, "invalid", "{}"])
def test_comparison_rejects_unverifiable_legacy_target(db: Session, snapshot) -> None:
    project, user, executions = _seed_experiment(db)
    executions[-1].target_snapshot = snapshot
    db.commit()
    with pytest.raises(HTTPException, match="recorded target snapshot"):
        create_comparison_report(
            db, project_id=project.id, created_by=user.id, name="Legacy",
            execution_ids=[execution.id for execution in executions],
        )


def test_comparison_discloses_rules_fallback(db: Session) -> None:
    from app.modules.control.models import ControlDecision
    from app.db.types import ControlAction

    project, user, executions = _seed_experiment(db)
    ai_ids = [execution.id for execution in executions if execution.strategy == ControlStrategy.AI_HYBRID]
    for window in db.scalars(select(MetricWindow).where(MetricWindow.execution_id.in_(ai_ids))):
        db.add(ControlDecision(
            metric_window_id=window.id, strategy=ControlStrategy.RULES,
            action=ControlAction.HOLD, previous_concurrency=2, next_concurrency=2,
            reason="No approved model",
        ))
    db.commit()
    comparison = create_comparison_report(
        db, project_id=project.id, created_by=user.id, name="Fallback",
        execution_ids=[execution.id for execution in executions],
    )
    evidence = json.loads(comparison.results_json)["ai_evidence"]
    assert evidence["fallback_windows"] == 9
    assert evidence["unverified_windows"] == 0
    assert "cannot be attributed exclusively" in comparison.conclusion
    assert json.loads(comparison.results_json)["warnings"][0]["code"] == "AI_INFERENCE_UNVERIFIED"


@pytest.mark.parametrize(
    "model_count,with_inference,expected_codes",
    [
        (1, True, []),
        (2, True, ["MODEL_VERSION_UNVERIFIED"]),
        (1, False, ["AI_INFERENCE_UNVERIFIED"]),
    ],
)
def test_comparison_structured_warnings_match_evidence(
    db: Session, model_count: int, with_inference: bool, expected_codes: list[str],
) -> None:
    from app.db.types import ControlAction, ModelStatus
    from app.modules.control.models import ControlDecision
    from app.modules.intelligence.models import ModelVersion, RiskPrediction

    project, user, executions = _seed_experiment(db)
    versions = [
        ModelVersion(
            version=f"test-model-{index}", algorithm="test", artifact_path="unused.joblib",
            status=ModelStatus.RETIRED, training_sample_count=10,
            training_dataset_hash="a" * 64, artifact_sha256="b" * 64,
        )
        for index in range(model_count)
    ]
    db.add_all(versions)
    db.flush()
    ai_executions = [
        execution for execution in executions
        if execution.strategy == ControlStrategy.AI_HYBRID
    ]
    for index, execution in enumerate(ai_executions):
        execution.model_version_id = versions[index % model_count].id
        if not with_inference:
            continue
        for window in db.scalars(select(MetricWindow).where(
            MetricWindow.execution_id == execution.id
        )):
            prediction = RiskPrediction(
                metric_window_id=window.id, model_version_id=execution.model_version_id,
                risk_probability=Decimal("0.1"), predicted_degradation=False,
                inference_latency_ms=1,
            )
            db.add(prediction)
            db.flush()
            db.add(ControlDecision(
                metric_window_id=window.id, risk_prediction_id=prediction.id,
                strategy=ControlStrategy.AI_HYBRID, action=ControlAction.HOLD,
                previous_concurrency=2, next_concurrency=2, reason="Test inference",
            ))
    db.commit()
    comparison = create_comparison_report(
        db, project_id=project.id, created_by=user.id, name="Structured warnings",
        execution_ids=[execution.id for execution in executions],
    )
    warnings = json.loads(comparison.results_json)["warnings"]
    assert [warning["code"] for warning in warnings] == expected_codes
    assert comparison.conclusion.count(" WARNING: ") == len(warnings)
    assert all(f" WARNING: {warning['message']}" in comparison.conclusion for warning in warnings)


@pytest.mark.integration
def test_comparison_survives_postgres_reconnection(monkeypatch) -> None:
    from alembic import command
    from alembic.config import Config

    configured = os.getenv("LOADFORGE_TEST_DATABASE_URL")
    if not configured:
        pytest.skip("LOADFORGE_TEST_DATABASE_URL is not set")
    url = make_url(configured)
    if not (url.database or "").endswith("_test"):
        pytest.fail("Integration tests require a database ending in _test")
    schema = "reports_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    isolated = url.update_query_dict({"options": f"-csearch_path={schema}"})
    database = create_engine(isolated)
    monkeypatch.setenv("DATABASE_URL", isolated.render_as_string(hide_password=False))
    try:
        command.upgrade(Config("alembic.ini"), "head")
        with Session(database, expire_on_commit=False) as db:
            project, user, executions = _seed_experiment(db)
            report = create_comparison_report(
                db, project_id=project.id, created_by=user.id, name="Persistence",
                execution_ids=[execution.id for execution in executions],
            )
            report_id, expected = report.id, report.results_json
        database.dispose()
        with Session(database) as reopened:
            assert reopened.get(ComparisonReport, report_id).results_json == expected
            assert len(list(reopened.scalars(select(ComparisonReportExecution)))) == 9
    finally:
        database.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
