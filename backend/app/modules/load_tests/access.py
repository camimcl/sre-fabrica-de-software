"""Internal scoped lookups shared by load-tests, intelligence and reports.

These functions do not commit or mutate data. Missing resources or resources
outside the supplied parent raise HTTP 404. Callers check project access first.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.load_tests.models import TestExecution, TestScenario


def require_scenario(db: Session, project_id: UUID, scenario_id: UUID) -> TestScenario:
    scenario = db.scalar(
        select(TestScenario).where(
            TestScenario.id == scenario_id, TestScenario.project_id == project_id
        )
    )
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


def require_execution(db: Session, scenario_id: UUID, execution_id: UUID) -> TestExecution:
    execution = db.scalar(
        select(TestExecution).where(
            TestExecution.id == execution_id,
            TestExecution.scenario_id == scenario_id,
        )
    )
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution
