from collections.abc import Iterator

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

    def override() -> Iterator[Session]:
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    engine.dispose()


def _qa(factory, email="qa@example.org") -> User:
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


def _token(client, email, password="strong-password-123") -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _project(client, headers, name="Dashboard project") -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def test_dashboard_empty_project_returns_zeros(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers)
    data = client.get(f"/projects/{project_id}/dashboard", headers=headers)
    assert data.status_code == 200, data.text
    body = data.json()
    assert body["totals"]["executions"] == 0
    assert body["completion_rate"] == 0.0
    assert body["timeseries_executions_per_day"] == []
    assert set(body["executions_by_status"]) == {
        "PENDING", "RUNNING", "COMPLETED", "CANCELLED", "FAILED"
    }


def test_dashboard_missing_project_404(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    from uuid import uuid4

    assert client.get(f"/projects/{uuid4()}/dashboard", headers=headers).status_code == 404


def test_project_search_is_case_insensitive(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    _project(client, headers, "Alpha Catalogue")
    _project(client, headers, "Beta Service")
    rows = client.get("/projects?search=alpha", headers=headers).json()
    assert [row["name"] for row in rows] == ["Alpha Catalogue"]
    assert client.get("/projects?search=   ", headers=headers).json().__len__() == 2


def test_executions_query_validates_date_range(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers)
    bad = client.get(
        f"/projects/{project_id}/executions?date_from=2026-02-01T00:00:00&date_to=2026-01-01T00:00:00",
        headers=headers,
    )
    assert bad.status_code == 422
    ok = client.get(f"/projects/{project_id}/executions", headers=headers)
    assert ok.status_code == 200
    assert ok.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_executions_query_rejects_bad_page(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers)
    assert client.get(
        f"/projects/{project_id}/executions?page=0", headers=headers
    ).status_code == 422
    assert client.get(
        f"/projects/{project_id}/executions?page_size=1000", headers=headers
    ).status_code == 422


def test_audit_log_requires_qa(api) -> None:
    client, factory = api
    # viewer
    client.post(
        "/auth/register",
        json={"full_name": "Viewer", "email": "v@example.org", "password": "viewer-pass-123"},
    )
    viewer = _token(client, "v@example.org", "viewer-pass-123")
    assert client.get("/audit/logs", headers=viewer).status_code == 403


def test_write_operation_is_audited(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers, "Audited project")
    logs = client.get("/audit/logs", headers=headers).json()
    assert logs["total"] >= 1
    entry = logs["items"][0]
    assert entry["entity_type"] == "project"
    assert entry["action"] == "CREATE"
    assert entry["entity_id"] == project_id


def test_export_executions_csv_headers(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers)
    response = client.get(f"/projects/{project_id}/exports/executions.csv", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "execution_id,scenario_name,strategy,status" in response.text
