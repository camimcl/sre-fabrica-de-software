import asyncio
from uuid import uuid4

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
