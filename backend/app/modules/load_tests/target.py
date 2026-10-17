"""Capture execution targets once and resolve them without mutating history."""

import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.load_tests.models import TestExecution, TestScenario
from app.modules.projects.models import Endpoint


WINDOW_DURATION_MS = 2000


def capture_target(endpoint: Endpoint) -> str:
    return json.dumps(
        {
            "endpoint_id": str(endpoint.id),
            "base_url": endpoint.base_url,
            "http_method": endpoint.http_method,
            "window_duration_ms": WINDOW_DURATION_MS,
        },
        sort_keys=True,
    )


def resolve_execution_target(db: Session, execution: TestExecution) -> dict:
    """Read the frozen target, checking that its current authorization still applies."""
    try:
        target = json.loads(execution.target_snapshot or "null")
        endpoint_id = UUID(target["endpoint_id"])
        if (
            not isinstance(target["base_url"], str)
            or not target["base_url"]
            or not isinstance(target["http_method"], str)
            or not target["http_method"]
            or type(target["window_duration_ms"]) is not int
            or target["window_duration_ms"] <= 0
        ):
            raise ValueError
    except (TypeError, KeyError, ValueError, AttributeError) as exc:
        raise ValueError(
            "Execution has no valid target snapshot; create a new execution"
        ) from exc

    endpoint = db.get(Endpoint, endpoint_id)
    scenario = db.get(TestScenario, execution.scenario_id)
    if endpoint is None or scenario is None or endpoint.project_id != scenario.project_id:
        raise ValueError("Recorded target is unavailable; create a new execution")
    if not endpoint.authorization_confirmed:
        raise ValueError("The recorded target must have confirmed authorization")
    if endpoint.base_url != target["base_url"] or endpoint.http_method != target["http_method"]:
        raise ValueError("Recorded target configuration has changed; create a new execution")
    return target
