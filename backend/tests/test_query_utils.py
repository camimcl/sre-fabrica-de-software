from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import Integer, String, create_engine, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from app.core.query import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    escape_like,
    normalized_search,
    paginate,
    validate_date_range,
)
from app.db.base import Base


class _Row(Base):
    __tablename__ = "query_util_rows"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _Row.__table__.create(engine)
    return Session(bind=engine)


def test_escape_like_neutralizes_wildcards() -> None:
    assert escape_like("100%_raw\\") == "100\\%\\_raw\\\\"


def test_normalized_search_blankness() -> None:
    assert normalized_search(None) is None
    assert normalized_search("   ") is None
    assert normalized_search("  abc ") == "abc"


def test_validate_date_range() -> None:
    a = datetime(2026, 1, 1, tzinfo=timezone.utc)
    b = datetime(2026, 2, 1, tzinfo=timezone.utc)
    validate_date_range(a, b)  # no error
    validate_date_range(None, None)
    validate_date_range(a, None)
    with pytest.raises(HTTPException) as exc:
        validate_date_range(b, a)
    assert exc.value.status_code == 422


def test_paginate_partitions_without_overlap() -> None:
    with _session() as db:
        for index in range(25):
            db.add(_Row(name=f"row-{index:02d}"))
        db.commit()
        base = select(_Row).order_by(_Row.name)

        page1, total = paginate(db, base, page=1, page_size=10)
        page2, _ = paginate(db, base, page=2, page_size=10)
        page3, _ = paginate(db, base, page=3, page_size=10)

        assert total == 25
        assert [r.name for r in page1] == [f"row-{i:02d}" for i in range(10)]
        assert len(page2) == 10
        assert len(page3) == 5
        ids = {r.id for r in page1 + page2 + page3}
        assert len(ids) == 25  # no overlap, no omission


def test_paginate_beyond_last_page_is_empty() -> None:
    with _session() as db:
        db.add(_Row(name="only"))
        db.commit()
        items, total = paginate(db, select(_Row).order_by(_Row.id), page=5, page_size=10)
        assert items == []
        assert total == 1


def test_page_size_bounds_are_defined() -> None:
    assert DEFAULT_PAGE_SIZE <= MAX_PAGE_SIZE
    assert DEFAULT_PAGE_SIZE >= 1
