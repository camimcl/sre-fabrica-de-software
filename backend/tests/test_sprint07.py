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


# --- Regression tests for the PR review ------------------------------------


def _endpoint(client, headers, project_id, confirmed=True) -> str:
    payload = {
        "name": "Target",
        "base_url": "https://example.com/api",
        "http_method": "GET",
        "authorization_confirmed": confirmed,
        "authorization_evidence": "ok" if confirmed else None,
    }
    return client.post(
        f"/projects/{project_id}/endpoints", json=payload, headers=headers
    ).json()["id"]


def _scenario(client, headers, project_id, endpoint_id, name="S") -> str:
    return client.post(
        f"/projects/{project_id}/scenarios",
        json={
            "name": name,
            "endpoint_id": endpoint_id,
            "duration_seconds": 1,
            "initial_concurrency": 1,
            "max_concurrency": 2,
            "ramp_up_per_window": 0,
            "timeout_ms": 1000,
            "strategy": "RULES",
            "p95_limit_ms": 800,
            "error_rate_limit": "0.5",
        },
        headers=headers,
    ).json()["id"]


def _execution(client, headers, project_id, scenario_id) -> str:
    return client.post(
        f"/projects/{project_id}/scenarios/{scenario_id}/executions",
        json={"authorization_acknowledged": True},
        headers=headers,
    ).json()["id"]


def test_comparison_export_routes_not_intercepted(api) -> None:
    # A non-existent comparison .csv/.pdf must reach the export route (404),
    # not be captured by the generic UUID route (which would 422).
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers)
    from uuid import uuid4

    cid = uuid4()
    csv = client.get(
        f"/projects/{project_id}/reports/comparisons/{cid}.csv", headers=headers
    )
    pdf = client.get(
        f"/projects/{project_id}/reports/comparisons/{cid}.pdf", headers=headers
    )
    assert csv.status_code == 404, csv.text
    assert pdf.status_code == 404, pdf.text


def test_execution_pdf_validates_scope(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers)
    endpoint_id = _endpoint(client, headers, project_id)
    scenario_id = _scenario(client, headers, project_id, endpoint_id)
    execution_id = _execution(client, headers, project_id, scenario_id)
    from uuid import uuid4

    # Wrong scenario in the path must be rejected (404), not leak the report.
    wrong = client.get(
        f"/projects/{project_id}/scenarios/{uuid4()}/executions/{execution_id}/report.pdf",
        headers=headers,
    )
    assert wrong.status_code == 404


def test_csv_export_respects_initiated_by(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers)
    endpoint_id = _endpoint(client, headers, project_id)
    scenario_id = _scenario(client, headers, project_id, endpoint_id)
    _execution(client, headers, project_id, scenario_id)
    from uuid import uuid4

    # Filter by a different user: CSV must contain only the header row.
    response = client.get(
        f"/projects/{project_id}/exports/executions.csv?initiated_by={uuid4()}",
        headers=headers,
    )
    assert response.status_code == 200
    data_lines = [line for line in response.text.splitlines() if line.strip()]
    assert len(data_lines) == 1  # header only


def test_csv_neutralizes_formula_injection(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    # Project name starting with '=' would be a spreadsheet formula.
    project_id = _project(client, headers, "=cmd|calc")
    endpoint_id = _endpoint(client, headers, project_id)
    scenario_id = _scenario(client, headers, project_id, endpoint_id, name="=DANGER()")
    _execution(client, headers, project_id, scenario_id)
    response = client.get(
        f"/projects/{project_id}/exports/executions.csv", headers=headers
    )
    assert response.status_code == 200
    # The scenario name cell must be prefixed with a quote, not a raw '='.
    assert "'=DANGER()" in response.text
    assert ",=DANGER()" not in response.text


def test_mixed_timezone_dates_do_not_500(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers)
    # date_from aware (with offset), date_to naive — must not raise 500.
    url = (
        f"/projects/{project_id}/executions"
        "?date_from=2026-01-01T00:00:00%2B00:00&date_to=2026-12-31T23:59:59"
    )
    response = client.get(url, headers=headers)
    assert response.status_code == 200, response.text
    # Dashboard too.
    dash = client.get(
        f"/projects/{project_id}/dashboard?date_from=2026-01-01T00:00:00%2B00:00&date_to=2026-12-31T23:59:59",
        headers=headers,
    )
    assert dash.status_code == 200, dash.text


def test_duplicate_project_returns_409_without_audit(api) -> None:
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    _project(client, headers, "Unique name")
    before = client.get("/audit/logs", headers=headers).json()["total"]
    conflict = client.post("/projects", json={"name": "Unique name"}, headers=headers)
    assert conflict.status_code == 409, conflict.text
    after = client.get("/audit/logs", headers=headers).json()["total"]
    assert after == before  # rejected op left no audit entry


def test_manual_execution_transitions_are_audited(api, monkeypatch) -> None:
    # Disable the load engine so manual transitions apply directly.
    from app.modules.load_tests import api as load_tests_api

    monkeypatch.setattr(load_tests_api, "ENGINE_ENABLED", False)
    client, factory = api
    qa = _qa(factory)
    headers = _token(client, qa.email)
    project_id = _project(client, headers)
    endpoint_id = _endpoint(client, headers, project_id)
    scenario_id = _scenario(client, headers, project_id, endpoint_id)
    execution_id = _execution(client, headers, project_id, scenario_id)
    base = f"/projects/{project_id}/scenarios/{scenario_id}/executions/{execution_id}"
    assert client.post(f"{base}/start", headers=headers).status_code == 200
    assert client.post(
        f"{base}/cancel", json={"cancellation_reason": "manual stop"}, headers=headers
    ).status_code == 200

    logs = client.get(
        "/audit/logs?entity_type=execution", headers=headers
    ).json()["items"]
    actions = [entry["summary"] for entry in logs]
    # Both a RUNNING start and a CANCELLED transition were recorded.
    assert any("RUNNING" in (s or "") for s in actions)
    assert any("CANCELLED" in (s or "") for s in actions)
