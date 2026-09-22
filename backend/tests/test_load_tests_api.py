from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.db.types import UserRole
from app.main import app
from app.modules.auth.models import User
from app.modules.load_tests.models import TestExecution


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, sessionmaker]]:
    monkeypatch.setenv(
        "LOADFORGE_TOKEN_SECRET", "test-only-secret-value-with-at-least-32-bytes"
    )
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def session_override() -> Iterator[Session]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = session_override
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    engine.dispose()


def _qa(factory: sessionmaker, email: str = "qa@example.org") -> User:
    with factory() as db:
        user = User(
            full_name="QA Tester",
            email=email,
            password_hash=hash_password("strong-password-123"),
            role=UserRole.QA,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def _token(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _project(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Load project"}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _endpoint(
    client: TestClient,
    project_id: str,
    headers: dict[str, str],
    confirmed: bool = True,
) -> str:
    payload = {
        "name": "Target",
        "base_url": "https://example.com/api",
        "http_method": "GET",
        "authorization_confirmed": confirmed,
        "authorization_evidence": "Authorized" if confirmed else None,
    }
    response = client.post(
        f"/projects/{project_id}/endpoints", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _scenario_payload(endpoint_id: str, **overrides) -> dict:
    payload = {
        "name": "Baseline",
        "endpoint_id": endpoint_id,
        "duration_seconds": 60,
        "initial_concurrency": 5,
        "max_concurrency": 50,
        "ramp_up_per_window": 2,
        "timeout_ms": 3000,
        "strategy": "RULES",
        "p95_limit_ms": 800,
        "error_rate_limit": "0.05000",
    }
    payload.update(overrides)
    return payload


def test_scenario_crud_and_persistence(api: tuple[TestClient, sessionmaker]) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email, "strong-password-123")
    project_id = _project(client, headers)
    endpoint_id = _endpoint(client, project_id, headers)

    created = client.post(
        f"/projects/{project_id}/scenarios",
        json=_scenario_payload(endpoint_id),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    scenario_id = created.json()["id"]
    assert created.json()["created_by"] == str(qa.id)

    listed = client.get(f"/projects/{project_id}/scenarios", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.put(
        f"/projects/{project_id}/scenarios/{scenario_id}",
        json=_scenario_payload(endpoint_id, name="Updated", max_concurrency=80),
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated"
    assert updated.json()["max_concurrency"] == 80

    # Persistence: reopen a session and confirm the record survives.
    with factory() as db:
        from app.modules.load_tests.models import TestScenario

        assert db.get(TestScenario, UUID(scenario_id)).name == "Updated"

    assert (
        client.delete(
            f"/projects/{project_id}/scenarios/{scenario_id}", headers=headers
        ).status_code
        == 204
    )
    assert (
        client.get(
            f"/projects/{project_id}/scenarios/{scenario_id}", headers=headers
        ).status_code
        == 404
    )


def test_scenario_validations(api: tuple[TestClient, sessionmaker]) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email, "strong-password-123")
    project_id = _project(client, headers)
    endpoint_id = _endpoint(client, project_id, headers)
    base = f"/projects/{project_id}/scenarios"

    # initial > max
    assert (
        client.post(
            base,
            json=_scenario_payload(endpoint_id, initial_concurrency=60),
            headers=headers,
        ).status_code
        == 422
    )
    # zero concurrency
    assert (
        client.post(
            base,
            json=_scenario_payload(endpoint_id, initial_concurrency=0),
            headers=headers,
        ).status_code
        == 422
    )
    # negative ramp up
    assert (
        client.post(
            base,
            json=_scenario_payload(endpoint_id, ramp_up_per_window=-1),
            headers=headers,
        ).status_code
        == 422
    )
    # error_rate_limit out of range
    assert (
        client.post(
            base,
            json=_scenario_payload(endpoint_id, error_rate_limit="1.5"),
            headers=headers,
        ).status_code
        == 422
    )
    # empty name
    assert (
        client.post(
            base, json=_scenario_payload(endpoint_id, name="   "), headers=headers
        ).status_code
        == 422
    )
    # invalid strategy
    assert (
        client.post(
            base,
            json=_scenario_payload(endpoint_id, strategy="TURBO"),
            headers=headers,
        ).status_code
        == 422
    )
    # extra field forbidden
    assert (
        client.post(
            base,
            json={**_scenario_payload(endpoint_id), "unexpected": 1},
            headers=headers,
        ).status_code
        == 422
    )


def test_authorization_invariant(api: tuple[TestClient, sessionmaker]) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email, "strong-password-123")
    project_id = _project(client, headers)
    unconfirmed = _endpoint(client, project_id, headers, confirmed=False)

    # endpoint without confirmed authorization -> 409
    blocked = client.post(
        f"/projects/{project_id}/scenarios",
        json=_scenario_payload(unconfirmed),
        headers=headers,
    )
    assert blocked.status_code == 409
    assert "authorization" in blocked.json()["detail"].lower()

    # endpoint from another project -> 404
    other_project = _project(client, headers)
    other_endpoint = _endpoint(client, other_project, headers)
    cross = client.post(
        f"/projects/{project_id}/scenarios",
        json=_scenario_payload(other_endpoint),
        headers=headers,
    )
    assert cross.status_code == 404


def test_permissions(api: tuple[TestClient, sessionmaker]) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email, "strong-password-123")
    project_id = _project(client, headers)
    endpoint_id = _endpoint(client, project_id, headers)

    # viewer cannot create
    viewer = {
        "full_name": "Viewer User",
        "email": "viewer@example.org",
        "password": "viewer-password-123",
    }
    client.post("/auth/register", json=viewer)
    viewer_headers = _token(client, viewer["email"], viewer["password"])
    assert (
        client.post(
            f"/projects/{project_id}/scenarios",
            json=_scenario_payload(endpoint_id),
            headers=viewer_headers,
        ).status_code
        == 403
    )

    # non-owner QA cannot create
    other = _qa(factory, "other@example.org")
    other_headers = _token(client, other.email, "strong-password-123")
    assert (
        client.post(
            f"/projects/{project_id}/scenarios",
            json=_scenario_payload(endpoint_id),
            headers=other_headers,
        ).status_code
        == 403
    )

    # unauthenticated read blocked
    assert client.get(f"/projects/{project_id}/scenarios").status_code == 401


def _make_execution(
    client: TestClient, headers: dict[str, str], acknowledged: bool = True
) -> tuple[str, str, str]:
    project_id = _project(client, headers)
    endpoint_id = _endpoint(client, project_id, headers)
    scenario_id = client.post(
        f"/projects/{project_id}/scenarios",
        json=_scenario_payload(endpoint_id),
        headers=headers,
    ).json()["id"]
    execution = client.post(
        f"/projects/{project_id}/scenarios/{scenario_id}/executions",
        json={"authorization_acknowledged": acknowledged},
        headers=headers,
    )
    assert execution.status_code == 201, execution.text
    return project_id, scenario_id, execution.json()["id"]


def test_execution_creation_snapshots_and_requires_ack(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email, "strong-password-123")
    project_id, scenario_id, execution_id = _make_execution(client, headers)

    fetched = client.get(
        f"/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}",
        headers=headers,
    ).json()
    assert fetched["status"] == "PENDING"
    assert fetched["initial_concurrency"] == 5
    assert fetched["max_concurrency"] == 50
    assert fetched["initiated_by"] == str(qa.id)

    # acknowledgement is required at creation
    endpoint_id = _endpoint(client, project_id, headers)
    scenario2 = client.post(
        f"/projects/{project_id}/scenarios",
        json=_scenario_payload(endpoint_id, name="Second"),
        headers=headers,
    ).json()["id"]
    rejected = client.post(
        f"/projects/{project_id}/scenarios/{scenario2}/executions",
        json={"authorization_acknowledged": False},
        headers=headers,
    )
    assert rejected.status_code == 422


def test_execution_lifecycle_happy_path(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email, "strong-password-123")
    project_id, scenario_id, execution_id = _make_execution(client, headers)
    base = f"/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}"

    started = client.post(f"{base}/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["status"] == "RUNNING"
    assert started.json()["started_at"] is not None

    completed = client.post(f"{base}/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["ended_at"] is not None


def test_execution_invalid_transition(api: tuple[TestClient, sessionmaker]) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email, "strong-password-123")
    project_id, scenario_id, execution_id = _make_execution(client, headers)
    base = f"/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}"

    # cannot complete a PENDING execution
    invalid = client.post(f"{base}/complete", headers=headers)
    assert invalid.status_code == 409
    assert invalid.json()["detail"] == "Invalid execution state transition"


def test_execution_cancel_with_reason(api: tuple[TestClient, sessionmaker]) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email, "strong-password-123")
    project_id, scenario_id, execution_id = _make_execution(client, headers)
    base = f"/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}"

    # cancel without reason -> 422
    assert client.post(f"{base}/cancel", json={}, headers=headers).status_code == 422

    cancelled = client.post(
        f"{base}/cancel",
        json={"cancellation_reason": "Emergency stop during demo"},
        headers=headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancellation_reason"] == "Emergency stop during demo"
    assert cancelled.json()["ended_at"] is not None

    # cannot cancel again (terminal state)
    again = client.post(
        f"{base}/cancel",
        json={"cancellation_reason": "Second attempt"},
        headers=headers,
    )
    assert again.status_code == 409


def test_start_requires_acknowledgement_persisted(
    api: tuple[TestClient, sessionmaker],
) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email, "strong-password-123")
    project_id, scenario_id, execution_id = _make_execution(client, headers)

    # Force the persisted execution to have acknowledgement false.
    with factory() as db:
        execution = db.get(TestExecution, UUID(execution_id))
        execution.authorization_acknowledged = False
        db.commit()

    base = f"/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}"
    blocked = client.post(f"{base}/start", headers=headers)
    assert blocked.status_code == 409
    assert "authorization_acknowledged" in blocked.json()["detail"]
