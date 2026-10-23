"""Audit recording: writes an OperationLog in the caller's transaction.

`record_operation` adds the log entry via `db.add` (no commit here) so it shares
the atomicity of the audited operation: if the caller rolls back, the log is
discarded; if the caller commits, the log is persisted together.
"""

import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.types import AuditAction
from app.modules.audit.models import OperationLog


SENSITIVE_KEYS = frozenset({"password", "password_hash", "access_token", "token"})


def _sanitize(values: dict | None) -> dict:
    if not values:
        return {}
    return {
        key: ("***" if key in SENSITIVE_KEYS else _coerce(value))
        for key, value in values.items()
    }


def _coerce(value):
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _diff(before: dict | None, after: dict | None) -> dict:
    before_clean = _sanitize(before)
    after_clean = _sanitize(after)
    if before and after:
        changed = {
            key: {"before": before_clean.get(key), "after": after_clean.get(key)}
            for key in after_clean
            if before_clean.get(key) != after_clean.get(key)
        }
        return {"changed": changed}
    if after:
        return {"after": after_clean}
    if before:
        return {"before": before_clean}
    return {}


def record_operation(
    db: Session,
    *,
    actor_id: UUID,
    action: AuditAction,
    entity_type: str,
    entity_id: UUID | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> OperationLog:
    summary = _diff(before, after)
    entry = OperationLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=json.dumps(summary, sort_keys=True) if summary else None,
    )
    db.add(entry)
    return entry
