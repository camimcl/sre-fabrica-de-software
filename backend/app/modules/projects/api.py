from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.api import current_user, qa_user
from app.modules.auth.models import User
from app.modules.projects.models import Endpoint, Project
from app.modules.projects.schemas import (
    EndpointResponse,
    EndpointWrite,
    ProjectResponse,
    ProjectWrite,
)


router = APIRouter(prefix="/projects", tags=["projects"])


def _project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _owned_project(db: Session, project_id: UUID, user: User) -> Project:
    project = _project(db, project_id)
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Project owner required")
    return project


def _endpoint(db: Session, project_id: UUID, endpoint_id: UUID) -> Endpoint:
    endpoint = db.scalar(
        select(Endpoint).where(
            Endpoint.id == endpoint_id, Endpoint.project_id == project_id
        )
    )
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return endpoint


def _commit(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=detail) from exc


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    _: User = Depends(current_user), db: Session = Depends(get_db)
) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at, Project.id)))


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    request: ProjectWrite,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> Project:
    project = Project(owner_id=user.id, **request.model_dump())
    db.add(project)
    _commit(db, "A project with this name already exists for this owner")
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Project:
    return _project(db, project_id)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    request: ProjectWrite,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> Project:
    project = _owned_project(db, project_id, user)
    for key, value in request.model_dump().items():
        setattr(project, key, value)
    _commit(db, "A project with this name already exists for this owner")
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: UUID,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> None:
    project = _owned_project(db, project_id, user)
    db.delete(project)
    _commit(db, "Remove dependent endpoints and scenarios before deleting the project")


@router.get("/{project_id}/endpoints", response_model=list[EndpointResponse])
def list_endpoints(
    project_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[Endpoint]:
    _project(db, project_id)
    return list(
        db.scalars(
            select(Endpoint)
            .where(Endpoint.project_id == project_id)
            .order_by(Endpoint.created_at, Endpoint.id)
        )
    )


@router.post("/{project_id}/endpoints", response_model=EndpointResponse, status_code=201)
def create_endpoint(
    project_id: UUID,
    request: EndpointWrite,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> Endpoint:
    _owned_project(db, project_id, user)
    values = request.model_dump()
    values["base_url"] = str(request.base_url)
    endpoint = Endpoint(project_id=project_id, **values)
    db.add(endpoint)
    _commit(db, "Endpoint could not be created")
    db.refresh(endpoint)
    return endpoint


@router.get("/{project_id}/endpoints/{endpoint_id}", response_model=EndpointResponse)
def get_endpoint(
    project_id: UUID,
    endpoint_id: UUID,
    _: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Endpoint:
    _project(db, project_id)
    return _endpoint(db, project_id, endpoint_id)


@router.put("/{project_id}/endpoints/{endpoint_id}", response_model=EndpointResponse)
def update_endpoint(
    project_id: UUID,
    endpoint_id: UUID,
    request: EndpointWrite,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> Endpoint:
    _owned_project(db, project_id, user)
    endpoint = _endpoint(db, project_id, endpoint_id)
    values = request.model_dump()
    values["base_url"] = str(request.base_url)
    for key, value in values.items():
        setattr(endpoint, key, value)
    _commit(db, "Endpoint could not be updated")
    db.refresh(endpoint)
    return endpoint


@router.delete("/{project_id}/endpoints/{endpoint_id}", status_code=204)
def delete_endpoint(
    project_id: UUID,
    endpoint_id: UUID,
    user: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> None:
    _owned_project(db, project_id, user)
    db.delete(_endpoint(db, project_id, endpoint_id))
    _commit(db, "Remove dependent scenarios before deleting the endpoint")
