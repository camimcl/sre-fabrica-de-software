from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.types import AuditAction


class OperationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    action: AuditAction
    entity_type: str
    entity_id: UUID | None
    summary: str | None
    created_at: datetime


class OperationLogPage(BaseModel):
    items: list[OperationLogResponse]
    total: int
    page: int
    page_size: int
