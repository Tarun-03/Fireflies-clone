import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse, Response

from app.api import (
    annotations,
    chat,
    exports,
    imports,
    meetings,
    search,
    segments,
    summary,
    tasks,
    transcript,
    workspace,
)
from app.api.errors import install_errors
from app.core.body_limit import BodyLimitMiddleware
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
            connection.execute(text("SELECT version_num FROM alembic_version"))
            available = connection.execute(
                text("SELECT sqlite_compileoption_used('ENABLE_FTS5')")
            ).scalar()
            if not available:
                return JSONResponse({"status": "unavailable"}, status_code=503)
    except SQLAlchemyError:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return JSONResponse({"status": "ok"})


app.add_middleware(BodyLimitMiddleware)
install_errors(app)
app.include_router(workspace.router)
app.include_router(imports.router)
app.include_router(meetings.router)
app.include_router(tasks.router)


@app.middleware("http")
async def request_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    started = time.monotonic()
    request.state.request_id = str(uuid4())
    result = await call_next(request)
    result.headers["X-Request-ID"] = request.state.request_id
    result.headers["Cache-Control"] = "no-store"
    result.headers["X-Content-Type-Options"] = "nosniff"
    route = getattr(request.scope.get("route"), "path", "unmatched")
    logging.getLogger("uvicorn.error").info(
        json.dumps(
            {
                "request_id": request.state.request_id,
                "method": request.method,
                "route": route,
                "status": result.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        )
    )
    return result


app.include_router(transcript.router)
app.include_router(summary.router)

app.include_router(segments.router)

app.include_router(annotations.router)

app.include_router(search.router)

app.include_router(chat.router)

app.include_router(exports.router)
