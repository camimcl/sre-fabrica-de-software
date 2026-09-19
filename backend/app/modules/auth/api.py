from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.projects.models import Project

from app.core.security import (
    TOKEN_LIFETIME_SECONDS,
    create_access_token,
    hash_password,
    read_access_token,
    verify_password,
)
from app.db.session import get_db
from app.db.types import UserRole
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)


router = APIRouter(tags=["auth"])
bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    user_id = read_access_token(credentials.credentials) if credentials else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def qa_user(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.QA:
        raise HTTPException(status_code=403, detail="QA role required")
    return user


def _create_user(db: Session, request: RegisterRequest, role: UserRole) -> User:
    user = User(
        full_name=request.full_name,
        email=str(request.email).lower(),
        password_hash=hash_password(request.password),
        role=role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    db.refresh(user)
    return user


def _user_or_404(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _can_manage_user(actor: User, target: User) -> None:
    if actor.role != UserRole.QA and actor.id != target.id:
        raise HTTPException(status_code=403, detail="You can only manage your own profile")


def _ensure_qa_remains(
    db: Session, target: User, next_role: UserRole | None = None
) -> None:
    removes_qa = target.role == UserRole.QA and (
        next_role is None or next_role != UserRole.QA
    )
    if not removes_qa:
        return
    qa_count = db.scalar(
        select(func.count()).select_from(User).where(User.role == UserRole.QA)
    )
    if qa_count is not None and qa_count <= 1:
        raise HTTPException(
            status_code=409, detail="The last QA account cannot be removed"
        )


def _ensure_no_orphan_projects(
    db: Session, target: User, next_role: UserRole
) -> None:
    """Block role demotion from QA when the user still owns projects.

    Project edit/delete routes require both QA role **and** ownership.
    Demoting the owner to VIEWER would leave those projects without anyone
    able to manage them.  The caller must transfer or remove the projects
    before changing the role.
    """
    if target.role != UserRole.QA or next_role == UserRole.QA:
        return
    project_count = db.scalar(
        select(func.count())
        .select_from(Project)
        .where(Project.owner_id == target.id)
    )
    if project_count:
        raise HTTPException(
            status_code=409,
            detail="Transfer or remove the user's projects before demoting from QA",
        )


@router.post("/auth/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> User:
    return _create_user(db, request, UserRole.VIEWER)


@router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == str(request.email).lower()))
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=TOKEN_LIFETIME_SECONDS,
    )


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/users", response_model=list[UserResponse])
def list_users(_: User = Depends(qa_user), db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at, User.id)))


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    request: UserCreateRequest,
    _: User = Depends(qa_user),
    db: Session = Depends(get_db),
) -> User:
    return _create_user(db, request, request.role)


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> User:
    target = _user_or_404(db, user_id)
    _can_manage_user(actor, target)
    if actor.role != UserRole.QA and request.role != target.role:
        raise HTTPException(status_code=403, detail="Only QA can change user roles")
    _ensure_qa_remains(db, target, request.role)
    _ensure_no_orphan_projects(db, target, request.role)

    target.full_name = request.full_name
    target.email = str(request.email).lower()
    # NOTE: role demotion is guarded by _ensure_no_orphan_projects above.
    # Demoting a QA who owns projects would leave them unmanageable because
    # project edit/delete require both QA role AND ownership.
    target.role = request.role
    if request.password:
        target.password_hash = hash_password(request.password)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    db.refresh(target)
    return target


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: UUID,
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    target = _user_or_404(db, user_id)
    _can_manage_user(actor, target)
    _ensure_qa_remains(db, target)
    db.delete(target)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Remove the user's projects and executions before deleting the account",
        ) from exc
