from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.query import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, paginate, validate_date_range
from app.db.session import get_db
from app.db.types import AuditAction
from app.modules.audit.models import OperationLog
from app.modules.audit.schemas import OperationLogPage
from app.modules.auth.api import qa_user
from app.modules.auth.models import User


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=OperationLogPage)
def list_operation_logs(
    actor_id: UUID | None = Query(None),
    action: AuditAction | None = Query(None),
    entity_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    _: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> OperationLogPage:
    validate_date_range(date_from, date_to)
    statement = select(OperationLog)
    if actor_id is not None:
        statement = statement.where(OperationLog.actor_id == actor_id)
    if action is not None:
        statement = statement.where(OperationLog.action == action)
    if entity_type is not None:
        statement = statement.where(OperationLog.entity_type == entity_type)
    if date_from is not None:
        statement = statement.where(OperationLog.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(OperationLog.created_at <= date_to)
    statement = statement.order_by(
        OperationLog.created_at.desc(), OperationLog.id.desc()
    )
    items, total = paginate(db, statement, page=page, page_size=page_size)
    return OperationLogPage(items=items, total=total, page=page, page_size=page_size)
