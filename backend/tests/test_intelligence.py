from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.db.types import ControlStrategy, ExecutionStatus, ModelStatus, UserRole
from app.modules.auth.models import User
from app.modules.intelligence.dataset import build_training_samples
from app.modules.intelligence.models import ModelVersion
from app.modules.intelligence.predictor import (
    ArtifactValidationError,
    SklearnRiskPredictor,
)
from app.modules.intelligence.training import approve_candidate, train_candidate
from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.metrics.models import MetricWindow
from app.modules.projects.models import Endpoint, Project
from app.main import app


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch):
    artifact_root = (
        Path(os.environ.get("LOADFORGE_TEST_ARTIFACT_ROOT", "../test-artifacts"))
        / str(uuid4())
    ).resolve()
    monkeypatch.setenv("LOADFORGE_MODEL_DIR", str(artifact_root))
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def _seed_windows(db: Session, count: int = 31) -> TestExecution:
    user = User(
        full_name="QA",
        email=f"qa-{uuid4()}@example.org",
        password_hash="x",
        role=UserRole.QA,
    )
    db.add(user)
    db.flush()
    project = Project(owner_id=user.id, name=f"P-{uuid4()}")
    db.add(project)
    db.flush()
    endpoint = Endpoint(
        project_id=project.id,
        name="target",
        base_url="http://127.0.0.1:9999",
        http_method="GET",
        authorization_confirmed=True,
        authorization_evidence="test",
    )
    db.add(endpoint)
    db.flush()
    scenario = TestScenario(
        project_id=project.id,
        endpoint_id=endpoint.id,
        created_by=user.id,
        name="training",
        duration_seconds=60,
        initial_concurrency=2,
        max_concurrency=30,
        ramp_up_per_window=1,
        timeout_ms=1000,
        strategy=ControlStrategy.AI_HYBRID,
        p95_limit_ms=500,
        error_rate_limit=Decimal("0.10"),
    )
    db.add(scenario)
    db.flush()
    execution = TestExecution(
        scenario_id=scenario.id,
        initiated_by=user.id,
        status=ExecutionStatus.COMPLETED,
        strategy=ControlStrategy.AI_HYBRID,
        duration_seconds=60,
        initial_concurrency=2,
        max_concurrency=30,
        ramp_up_per_window=1,
        timeout_ms=1000,
        p95_limit_ms=500,
        error_rate_limit=Decimal("0.10"),
        authorization_acknowledged=True,
    )
    db.add(execution)
    db.flush()
    start = datetime.now(timezone.utc)
    for sequence in range(count):
        degraded = sequence % 2 == 1
        db.add(
            MetricWindow(
                execution_id=execution.id,
                sequence_number=sequence,
                window_started_at=start + timedelta(seconds=sequence * 2),
                window_duration_ms=2000,
                concurrency=sequence + 1,
                request_count=100,
                success_count=80 if degraded else 100,
                timeout_count=5 if degraded else 0,
                throughput_rps=Decimal("35") if degraded else Decimal("50"),
                latency_p50_ms=Decimal("250") if degraded else Decimal("80"),
                latency_p95_ms=Decimal("800") if degraded else Decimal("150"),
                latency_p99_ms=Decimal("1000") if degraded else Decimal("220"),
                error_rate=Decimal("0.20") if degraded else Decimal("0"),
                cpu_percent=Decimal("0"),
                memory_mb=Decimal("128"),
            )
        )
    db.commit()
    return execution


def test_dataset_uses_next_window_as_temporal_label(db: Session) -> None:
    _seed_windows(db)
    samples = build_training_samples(db)
    assert len(samples) == 30
    assert samples[0].degraded_next_window is True
    assert samples[1].degraded_next_window is False
    assert samples[1].features.latency_p95_trend > 0


def test_train_version_approve_and_predict(db: Session) -> None:
    _seed_windows(db)
    model = train_candidate(db)

    assert model.status == ModelStatus.CANDIDATE
    assert model.training_sample_count == 30
    assert model.algorithm in {"logistic-regression", "random-forest"}
    assert model.f1_score is not None
    assert len(model.training_dataset_hash) == 64
    assert len(model.artifact_sha256) == 64

    approved = approve_candidate(db, model)
    assert approved.status == ModelStatus.APPROVED
    predictor = SklearnRiskPredictor(approved)
    sample = build_training_samples(db)[0]
    result = predictor.predict_risk(sample.features)
    assert 0 <= result.probability <= 1
    assert result.model_version == model.version


def test_approval_retires_previous_model(db: Session) -> None:
    _seed_windows(db)
    first = approve_candidate(db, train_candidate(db))
    second = approve_candidate(db, train_candidate(db))
    db.refresh(first)
    assert first.status == ModelStatus.RETIRED
    assert second.status == ModelStatus.APPROVED
    assert len(
        list(
            db.scalars(
                select(ModelVersion).where(
                    ModelVersion.status == ModelStatus.APPROVED
                )
            )
        )
    ) == 1


def test_tampered_artifact_is_rejected(db: Session) -> None:
    _seed_windows(db)
    model = train_candidate(db)
    artifact = Path(os.environ["LOADFORGE_MODEL_DIR"]) / model.artifact_path
    artifact.write_bytes(artifact.read_bytes() + b"tampered")
    with pytest.raises(ArtifactValidationError, match="integrity"):
        SklearnRiskPredictor(model)


def test_model_api_trains_lists_and_approves(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "LOADFORGE_TOKEN_SECRET", "test-only-secret-value-with-at-least-32-bytes"
    )
    execution = _seed_windows(db)
    user = db.get(User, execution.initiated_by)
    user.password_hash = hash_password("strong-password-123")
    db.commit()

    def session_override():
        yield db

    app.dependency_overrides[get_db] = session_override
    try:
        with TestClient(app) as client:
            login = client.post(
                "/auth/login",
                json={"email": user.email, "password": "strong-password-123"},
            )
            headers = {
                "Authorization": f"Bearer {login.json()['access_token']}"
            }
            trained = client.post(
                "/intelligence/models/train", headers=headers
            )
            assert trained.status_code == 201, trained.text
            assert trained.json()["status"] == "CANDIDATE"
            assert trained.json()["training_sample_count"] == 30

            listed = client.get("/intelligence/models", headers=headers)
            assert listed.status_code == 200
            assert listed.json()[0]["id"] == trained.json()["id"]

            approved = client.post(
                f"/intelligence/models/{trained.json()['id']}/approve",
                headers=headers,
            )
            assert approved.status_code == 200, approved.text
            assert approved.json()["status"] == "APPROVED"
    finally:
        app.dependency_overrides.clear()
