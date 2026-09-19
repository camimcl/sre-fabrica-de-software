"""Run with LOADFORGE_TEST_DATABASE_URL after applying Alembic migrations."""

import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.db.session import get_db, get_engine
from app.db.types import UserRole
from app.main import app
from app.modules.auth.models import User
from app.modules.projects.models import Endpoint, Project


@pytest.mark.integration
def test_postgres_migration_and_api_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = os.getenv("LOADFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("LOADFORGE_TEST_DATABASE_URL is not set")
    if not (make_url(database_url).database or "").endswith("_test"):
        pytest.fail("Integration tests require a database ending in _test")

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("LOADFORGE_TOKEN_SECRET", "integration-test-secret-with-at-least-32-bytes")
    get_engine.cache_clear()
    engine = create_engine(database_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    email = f"qa-{uuid4().hex}@example.org"
    with factory() as db:
        user = User(
            full_name="Postgres QA",
            email=email,
            password_hash=hash_password("integration-password-123"),
            role=UserRole.QA,
        )
        db.add(user)
        db.commit()
        user_id = user.id

    def session_override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = session_override
    project_id = endpoint_id = None
    try:
        with TestClient(app) as client:
            assert client.get("/health/ready").json() == {
                "status": "ok", "database": "connected"
            }
            login = client.post(
                "/auth/login", json={"email": email, "password": "integration-password-123"}
            )
            assert login.status_code == 200, login.text
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            project = client.post("/projects", json={"name": "Postgres integration"}, headers=headers)
            assert project.status_code == 201, project.text
            project_id = UUID(project.json()["id"])
            endpoint = client.post(
                f"/projects/{project_id}/endpoints",
                json={"name": "Target", "base_url": "https://example.org/api"},
                headers=headers,
            )
            assert endpoint.status_code == 201, endpoint.text
            endpoint_id = UUID(endpoint.json()["id"])
            with factory() as db:
                assert db.scalar(select(Project.name).where(Project.id == project_id)) == "Postgres integration"
                assert db.scalar(select(Endpoint.name).where(Endpoint.id == endpoint_id)) == "Target"
            assert client.delete(
                f"/projects/{project_id}/endpoints/{endpoint_id}", headers=headers
            ).status_code == 204
            endpoint_id = None
            assert client.delete(f"/projects/{project_id}", headers=headers).status_code == 204
            project_id = None
    finally:
        app.dependency_overrides.clear()
        with factory() as db:
            if endpoint_id:
                db.query(Endpoint).filter(Endpoint.id == endpoint_id).delete()
            if project_id:
                db.query(Project).filter(Project.id == project_id).delete()
            db.query(User).filter(User.id == user_id).delete()
            db.commit()
        engine.dispose()
        get_engine.cache_clear()
