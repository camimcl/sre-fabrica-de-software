from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.db.types import UserRole
from app.main import app
from app.modules.auth.models import User
from app.modules.projects.models import Endpoint, Project


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, sessionmaker]]:
    monkeypatch.setenv("LOADFORGE_TOKEN_SECRET", "test-only-secret-value-with-at-least-32-bytes")
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


def test_registration_login_and_roles(api: tuple[TestClient, sessionmaker]) -> None:
    client, factory = api
    registration = {
        "full_name": "Viewer User",
        "email": "VIEWER@EXAMPLE.ORG",
        "password": "viewer-password-123",
    }
    created = client.post("/auth/register", json=registration)
    assert created.status_code == 201
    assert created.json()["role"] == "VIEWER"
    assert "password_hash" not in created.json()
    assert client.post("/auth/register", json={**registration, "role": "QA"}).status_code == 422
    assert client.post("/auth/register", json=registration).status_code == 409
    assert client.post(
        "/auth/login", json={"email": registration["email"], "password": "wrong"}
    ).status_code == 401

    viewer = _token(client, registration["email"], registration["password"])
    assert client.get("/auth/me", headers=viewer).json()["role"] == "VIEWER"
    assert client.post("/projects", json={"name": "Blocked"}, headers=viewer).status_code == 403
    assert client.post("/users", json={**registration, "role": "QA"}, headers=viewer).status_code == 403
    assert client.get("/projects").status_code == 401

    _qa(factory)
    qa = _token(client, "qa@example.org", "strong-password-123")
    new_qa = client.post(
        "/users",
        json={"full_name": "Second QA", "email": "second@example.org", "password": "second-password-123", "role": "QA"},
        headers=qa,
    )
    assert new_qa.status_code == 201
    assert new_qa.json()["role"] == "QA"
    assert len(client.get("/users", headers=qa).json()) == 3


def test_project_and_endpoint_crud_persists(api: tuple[TestClient, sessionmaker]) -> None:
    client, factory = api
    qa_user = _qa(factory)
    qa = _token(client, qa_user.email, "strong-password-123")
    project = client.post(
        "/projects", json={"name": "Catalogue API", "description": "Authorized test"}, headers=qa
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    assert client.get(f"/projects/{project_id}", headers=qa).json()["name"] == "Catalogue API"
    endpoint_data = {
        "name": "Products",
        "base_url": "https://example.com/products",
        "http_method": "get",
        "authorization_confirmed": True,
        "authorization_evidence": "Written authorization on file",
    }
    invalid = client.post(
        f"/projects/{project_id}/endpoints",
        json={**endpoint_data, "authorization_evidence": None},
        headers=qa,
    )
    assert invalid.status_code == 422
    endpoint = client.post(
        f"/projects/{project_id}/endpoints", json=endpoint_data, headers=qa
    )
    assert endpoint.status_code == 201, endpoint.text
    endpoint_id = endpoint.json()["id"]
    assert endpoint.json()["http_method"] == "GET"
    assert client.get(
        f"/projects/{project_id}/endpoints/{endpoint_id}", headers=qa
    ).json()["name"] == "Products"

    updated = client.put(
        f"/projects/{project_id}",
        json={"name": "Catalogue API v2", "description": "Changed"},
        headers=qa,
    )
    assert updated.status_code == 200
    changed_endpoint = client.put(
        f"/projects/{project_id}/endpoints/{endpoint_id}",
        json={**endpoint_data, "name": "Items", "authorization_confirmed": False},
        headers=qa,
    )
    assert changed_endpoint.status_code == 200

    with factory() as db:
        assert db.get(Project, UUID(project_id)).name == "Catalogue API v2"
        assert db.get(Endpoint, UUID(endpoint_id)).name == "Items"

    other = _qa(factory, "other@example.org")
    other_token = _token(client, other.email, "strong-password-123")
    assert client.put(
        f"/projects/{project_id}", json={"name": "Hijacked"}, headers=other_token
    ).status_code == 403
    assert client.delete(f"/projects/{project_id}", headers=qa).status_code == 409
    assert client.delete(f"/projects/{project_id}/endpoints/{endpoint_id}", headers=qa).status_code == 204
    assert client.delete(f"/projects/{project_id}", headers=qa).status_code == 204
    assert client.get(f"/projects/{project_id}", headers=qa).status_code == 404
