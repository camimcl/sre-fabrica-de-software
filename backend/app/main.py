from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_engine
from app.modules.auth.api import router as auth_router
from app.modules.intelligence.api import execution_router as intelligence_execution_router
from app.modules.intelligence.api import router as intelligence_router
from app.modules.load_tests.api import router as load_tests_router
from app.modules.projects.api import router as projects_router
from app.modules.reports.api import router as reports_router
from app.modules.audit.api import router as audit_router
from app.modules.dashboard.api import router as dashboard_router
from app.modules.exports.api import router as exports_router


app = FastAPI(title="LoadForge API", version="0.7.0")
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(load_tests_router)
app.include_router(intelligence_router)
app.include_router(intelligence_execution_router)
app.include_router(reports_router)
app.include_router(dashboard_router)
app.include_router(audit_router)
app.include_router(exports_router)


@app.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def ready() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "database": "connected"}
