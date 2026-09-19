from dataclasses import dataclass, field
import os

from app.core.database_url import postgresql_url_from_environment


def _required_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    return database_url or postgresql_url_from_environment()


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = field(default_factory=_required_database_url)
