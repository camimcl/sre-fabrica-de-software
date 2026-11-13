"""Single-process runtime ownership and recovery, enabled explicitly by deployment."""
import asyncio
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
import os

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.db.types import AuditAction, ExecutionStatus
from app.modules.audit.service import record_operation
from app.modules.load_tests.engine import registry
from app.modules.load_tests.models import TestExecution

RUNTIME_LOCK = 5498687522934632775
RECOVERY_REASON = 'Processo anterior interrompido; execução encerrada sem reiniciar tráfego.'


@contextmanager
def runtime_owner(engine):
    """Hold a PostgreSQL session lock until all traffic has been drained."""
    if engine.dialect.name != 'postgresql':
        raise RuntimeError('Managed execution runtime requires PostgreSQL')
    with engine.connect() as connection:
        acquired = connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': RUNTIME_LOCK})
        connection.commit()
        if not acquired:
            raise RuntimeError('Another LoadForge API owns this database; use exactly one API worker')
        try:
            yield
        finally:
            connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': RUNTIME_LOCK})
            connection.commit()


def recover_interrupted_executions(engine) -> int:
    """Requires runtime ownership. Preserve snapshots, metrics and terminal rows."""
    with Session(engine) as db:
        rows = list(db.scalars(select(TestExecution).where(
            TestExecution.status == ExecutionStatus.RUNNING).with_for_update()))
        for execution in rows:
            execution.status = ExecutionStatus.FAILED
            execution.ended_at = datetime.now(timezone.utc)
            execution.cancellation_reason = RECOVERY_REASON
            record_operation(db, actor_id=execution.initiated_by,
                             action=AuditAction.EXECUTE, entity_type='execution',
                             entity_id=execution.id, before={'status': 'RUNNING'},
                             after={'status': 'FAILED', 'origin': 'recovery', 'reason': RECOVERY_REASON})
        db.commit()
        return len(rows)


@asynccontextmanager
async def lifespan(app):
    enabled = os.getenv('LOADFORGE_MANAGED_RUNTIME', '0')
    if enabled not in ('0', '1'):
        raise RuntimeError('LOADFORGE_MANAGED_RUNTIME must be 0 or 1')
    if enabled == '0':
        try:
            yield
        finally:
            await registry.shutdown()
        return
    engine = get_engine()
    owner = runtime_owner(engine)
    await asyncio.to_thread(owner.__enter__)
    try:
        app.state.recovered_executions = await asyncio.to_thread(recover_interrupted_executions, engine)
        try:
            yield
        finally:
            await registry.shutdown()
    finally:
        await asyncio.to_thread(owner.__exit__, None, None, None)
