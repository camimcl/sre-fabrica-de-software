"""Internal project access contract shared by API modules.

These lookups do not commit or mutate data. Missing projects raise HTTP 404;
ownership violations raise HTTP 403. Callers enforce authentication and roles.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.projects.models import Project


def require_project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def require_owned_project(db: Session, project_id: UUID, user: User) -> Project:
    project = require_project(db, project_id)
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Project owner required")
    return project
