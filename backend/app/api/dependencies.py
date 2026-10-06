import hmac
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.limits import rate_limit
from app.db.engine import engine
from app.db.session import begin_write
from app.models import demo_sessions, memberships


@dataclass
class Scope:
    db: Session
    workspace_id: str
    user_id: str
    session_id: str


def service_auth(authorization: Annotated[str | None, Header()] = None) -> None:
    expected = "Bearer " + get_settings().internal_api_token.get_secret_value()
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise DomainError(401, "unauthorized", "Service authentication is required.")


def session_header(x_demo_session: Annotated[str | None, Header()] = None) -> str:
    try:
        if x_demo_session is None:
            raise ValueError()
        return str(UUID(x_demo_session))
    except ValueError as exc:
        raise DomainError(401, "session_required", "Start a demo session to continue.") from exc


def get_scope(
    request: Request,
    session_id: Annotated[str, Depends(session_header)],
    authenticated: Annotated[None, Depends(service_auth)],
) -> Iterator[Scope]:
    unsafe = request.method not in {"GET", "HEAD", "OPTIONS"}
    rate_limit(session_id, "write" if unsafe else "read", 30 if unsafe else 120)
    with Session(engine) as db:
        if unsafe:
            begin_write(db)
        row = (
            db.execute(
                select(demo_sessions)
                .join(
                    memberships,
                    (memberships.c.workspace_id == demo_sessions.c.workspace_id)
                    & (memberships.c.user_id == demo_sessions.c.user_id),
                )
                .where(demo_sessions.c.id == session_id)
            )
            .mappings()
            .first()
        )
        if row is None or datetime.fromisoformat(row["expires_at"]) <= datetime.now(UTC):
            raise DomainError(
                401, "session_expired", "Your demo session has expired. Start a new session."
            )
        yield Scope(db, str(row["workspace_id"]), str(row["user_id"]), session_id)
        if unsafe:
            db.commit()


Scoped = Annotated[Scope, Depends(get_scope, scope="function")]


def require_version(actual: int, header: str | None) -> None:
    if header is None:
        raise DomainError(428, "version_required", "Reload this item before changing it.")
    if header.strip('"') != str(actual):
        raise DomainError(
            409,
            "version_conflict",
            "This item changed. Reload it before retrying; your draft is retained.",
        )


Version = Annotated[str | None, Header(alias="If-Match")]
