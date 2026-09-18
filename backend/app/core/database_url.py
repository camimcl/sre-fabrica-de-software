import os
from urllib.parse import quote


_REQUIRED_COMPONENTS = (
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
)


def postgresql_url_from_environment() -> str:
    missing = [name for name in _REQUIRED_COMPONENTS if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Database connection variables must be set: " + ", ".join(missing)
        )

    port = int(os.environ["POSTGRES_PORT"])
    username = quote(os.environ["POSTGRES_USER"], safe="")
    password = quote(os.environ["POSTGRES_PASSWORD"], safe="")
    database = quote(os.environ["POSTGRES_DB"], safe="")
    host = os.environ["POSTGRES_HOST"]
    return f"postgresql+psycopg://{username}:{password}@{host}:{port}/{database}"
