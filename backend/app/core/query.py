"""Shared query helpers: pagination, text search and date-range filtering.

These utilities are storage-agnostic (work on SQLAlchemy 2.0 Select objects)
and do not commit or mutate data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def escape_like(term: str) -> str:
    """Escape user input so LIKE wildcards are treated literally.

    Uses backslash as the escape character; callers must pass escape="\\".
    """
    return (
        term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )


def normalized_search(term: str | None) -> str | None:
    """Return a trimmed search term, or None when blank/absent."""
    if term is None:
        return None
    cleaned = term.strip()
    return cleaned or None


def validate_date_range(
    date_from: datetime | None, date_to: datetime | None
) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=422, detail="date_from must not be after date_to"
        )


def paginate(
    db: Session, statement: Select, *, page: int, page_size: int
) -> tuple[list, int]:
    """Return (items, total) for a Select, applying COUNT and limit/offset.

    `page` is 1-based. The caller is responsible for ordering the statement
    deterministically before pagination.
    """
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = list(
        db.scalars(statement.limit(page_size).offset((page - 1) * page_size))
    )
    return rows, total
