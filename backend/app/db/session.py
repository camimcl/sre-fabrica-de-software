from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(Settings().database_url, pool_pre_ping=True)


def get_db():
    session = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
