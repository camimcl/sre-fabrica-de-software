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


def test_user_update_delete_and_permissions(api: tuple[TestClient, sessionmaker]) -> None:
    client, factory = api
    first_viewer = {
        "full_name": "First Viewer",
        "email": "first-viewer@example.org",
        "password": "first-viewer-password-123",
    }
    second_viewer = {
        "full_name": "Second Viewer",
        "email": "second-viewer@example.org",
        "password": "second-viewer-password-123",
    }
    first_id = client.post("/auth/register", json=first_viewer).json()["id"]
    second_id = client.post("/auth/register", json=second_viewer).json()["id"]
    viewer = _token(client, first_viewer["email"], first_viewer["password"])

    self_update = {
        "full_name": "Updated Viewer",
        "email": "updated-viewer@example.org",
        "password": "updated-viewer-password-123",
        "role": "VIEWER",
    }
    updated = client.put(f"/users/{first_id}", json=self_update, headers=viewer)
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Updated Viewer"
    assert updated.json()["email"] == "updated-viewer@example.org"
    assert _token(client, self_update["email"], self_update["password"])

    escalation = client.put(
        f"/users/{first_id}",
        json={**self_update, "role": "QA"},
        headers=viewer,
    )
    assert escalation.status_code == 403
    assert client.put(
        f"/users/{second_id}",
        json={**second_viewer, "password": None, "role": "VIEWER"},
        headers=viewer,
    ).status_code == 403

    qa_user = _qa(factory)
    qa = _token(client, qa_user.email, "strong-password-123")
    promoted = client.put(
        f"/users/{second_id}",
        json={**second_viewer, "password": None, "role": "QA"},
        headers=qa,
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "QA"
    second_qa = _token(client, second_viewer["email"], second_viewer["password"])
    owned_project = client.post(
        "/projects", json={"name": "Owned project"}, headers=second_qa
    )
    assert owned_project.status_code == 201, owned_project.text
    assert client.delete(f"/users/{second_id}", headers=qa).status_code == 409
    assert client.delete(
        f"/projects/{owned_project.json()['id']}", headers=second_qa
    ).status_code == 204
    assert client.delete(f"/users/{second_id}", headers=qa).status_code == 204
    assert client.delete(f"/users/{qa_user.id}", headers=qa).status_code == 409

    refreshed_viewer = _token(client, self_update["email"], self_update["password"])
    assert client.delete(f"/users/{first_id}", headers=refreshed_viewer).status_code == 204
    assert client.get("/auth/me", headers=refreshed_viewer).status_code == 401


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
