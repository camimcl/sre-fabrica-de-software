from dataclasses import dataclass, field
import os


def _required_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set")
    return database_url


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str = field(default_factory=_required_database_url)
