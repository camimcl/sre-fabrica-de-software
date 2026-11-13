import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url

from test_api import api  # noqa: F401
from test_sprint08_permissions import resources  # noqa: F401
from app.modules.audit.models import OperationLog
from app.modules.load_tests.models import TestExecution
from app.runtime import recover_interrupted_executions, runtime_owner

from app.db.types import ExecutionStatus
from app.modules.load_tests import engine


def test_forced_task_cancellation_records_terminal_failure(monkeypatch):
    finalized = []
    plan = dict(duration_seconds=30, timeout_ms=1000, authorization_confirmed=True,
                base_url='http://127.0.0.1', http_method='GET', initial_concurrency=1,
                max_concurrency=1, ramp_up_per_window=0, strategy='FIXED', window_duration_ms=2000)
    monkeypatch.setattr(engine, '_load_plan', lambda _: plan)
    monkeypatch.setattr(engine, '_load_approved_predictor', lambda _: (None, None))
    monkeypatch.setattr(engine, '_finalize_execution', lambda *args: finalized.append(args))

    async def exercise():
        entered = asyncio.Event()
        async def window(**kwargs):
            entered.set()
            await asyncio.sleep(60)
        monkeypatch.setattr(engine, '_run_window', window)
        execution_id = uuid4()
        task = asyncio.create_task(engine.run_execution(execution_id, asyncio.Event()))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert finalized and finalized[0][0] == execution_id
        assert finalized[0][1] == ExecutionStatus.FAILED
    asyncio.run(exercise())


def test_shutdown_signals_and_drains_registered_tasks():
    async def exercise():
        registry = engine.EngineRegistry()
        identifier = uuid4()
        event = registry.register(identifier)
        finished = []
        async def active():
            await event.wait()
            finished.append(True)
            registry.finish(identifier)
        task = asyncio.create_task(active())
        registry.track_task(identifier, task)
        await registry.shutdown(timeout=1)
        assert finished and task.done() and not registry.is_running(identifier)
    asyncio.run(exercise())


def test_recovery_is_idempotent_and_preserves_history(resources):
    r = resources
    with r['factory']() as db:
        execution = db.get(TestExecution, UUID(r['execution']))
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        snapshot = execution.target_snapshot
        db.commit()
    database = r['factory'].kw['bind']
    assert recover_interrupted_executions(database) == 1
    assert recover_interrupted_executions(database) == 0
    with r['factory']() as db:
        execution = db.get(TestExecution, UUID(r['execution']))
        assert execution.status == ExecutionStatus.FAILED
        assert execution.ended_at is not None and execution.target_snapshot == snapshot
        events = list(db.scalars(select(OperationLog).where(OperationLog.entity_id == execution.id)))
        assert len(events) == 1 and 'recovery' in events[0].summary


@pytest.mark.integration
def test_runtime_lease_rejects_a_second_api_and_releases_after_shutdown():
    url = os.getenv('LOADFORGE_TEST_DATABASE_URL')
    if not url:
        pytest.skip('LOADFORGE_TEST_DATABASE_URL is not set')
    assert (make_url(url).database or '').endswith('_test')
    database = create_engine(url)
    try:
        with runtime_owner(database):
            with pytest.raises(RuntimeError, match='Another LoadForge API'):
                with runtime_owner(database):
                    pytest.fail('A second runtime acquired ownership')
        with runtime_owner(database):
            pass
    finally:
        database.dispose()
