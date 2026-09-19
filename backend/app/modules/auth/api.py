from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
