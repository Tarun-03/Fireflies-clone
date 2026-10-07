import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import anyio.to_thread
from alembic.config import Config
from alembic.script import ScriptDirectory
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    anyio.to_thread.current_default_thread_limiter().total_tokens = 8
    yield


@lru_cache(maxsize=1)
def migration_heads() -> set[str]:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    return set(ScriptDirectory.from_config(config).get_heads())


app = FastAPI(
    lifespan=lifespan,
    title="Meeting workspace",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts.split(","))


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> JSONResponse:
    try:
        with engine.connect() as connection:
            versions = set(connection.scalars(text("SELECT version_num FROM alembic_version")))
            if versions != migration_heads():
                return JSONResponse({"status": "unavailable"}, status_code=503)
            if connection.scalar(text("PRAGMA foreign_keys")) != 1:
                return JSONResponse({"status": "unavailable"}, status_code=503)
            # Exercise the virtual table and MATCH implementation, not a build flag.
            connection.execute(
                text(
                    "SELECT rowid FROM search_documents_fts "
                    "WHERE search_documents_fts MATCH 'readinessprobe' LIMIT 1"
                )
            ).all()
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
