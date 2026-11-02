"""PostgreSQL evidence for the last-QA invariant under competing requests."""

from concurrent.futures import ThreadPoolExecutor
import os
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from app.db.base import Base
from app.db.session import get_db
from app.db.types import UserRole
from app.main import app
from app.modules.auth import api as auth_api
from app.modules.auth.models import User
from test_api import _qa, _token


@pytest.mark.integration
def test_two_qas_cannot_demote_each_other_out_of_administration(monkeypatch):
    url = os.getenv('LOADFORGE_TEST_DATABASE_URL')
    if not url:
        pytest.skip('LOADFORGE_TEST_DATABASE_URL is not set')
    assert (make_url(url).database or '').endswith('_test')
    monkeypatch.setenv('LOADFORGE_TOKEN_SECRET', 'sprint08-concurrency-test-secret-with-32-bytes')
    engine = create_engine(url)
    schema = f's8_permissions_{uuid4().hex}'
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    factory = sessionmaker(bind=scoped, expire_on_commit=False)
    try:
        Base.metadata.create_all(scoped)
        first = _qa(factory, 'first@example.org')
        second = _qa(factory, 'second@example.org')

        def sessions():
            with factory() as db:
                yield db

        app.dependency_overrides[get_db] = sessions
        with TestClient(app) as client:
            headers = [_token(client, user.email, 'strong-password-123') for user in (first, second)]
            rendezvous = Barrier(2)
            original = auth_api._ensure_qa_remains

            def simultaneous(db, target, next_role=None):
                rendezvous.wait(timeout=15)
                return original(db, target, next_role)

            monkeypatch.setattr(auth_api, '_ensure_qa_remains', simultaneous)

            def demote(index):
                user = (first, second)[index]
                return client.put(f'/users/{user.id}', headers=headers[index], json={
                    'full_name': user.full_name, 'email': user.email,
                    'role': 'VIEWER', 'password': None,
                }).status_code

            with ThreadPoolExecutor(max_workers=2) as pool:
                statuses = list(pool.map(demote, [0, 1]))
            assert sorted(statuses) == [200, 409]
        with factory() as db:
            assert db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.QA)) == 1
    finally:
        app.dependency_overrides.clear()
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()
