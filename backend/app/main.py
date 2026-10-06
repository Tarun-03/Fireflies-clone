from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.db.engine import engine

settings = get_settings()
app = FastAPI(
    title="Meeting workspace", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts.split(","))


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            available = connection.execute(
                text("SELECT sqlite_compileoption_used('ENABLE_FTS5')")
            ).scalar()
            if not available:
                return JSONResponse({"status": "unavailable"}, status_code=503)
    except SQLAlchemyError:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return JSONResponse({"status": "ok"})
