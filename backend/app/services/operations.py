"""Short SQLite transactions claim and complete costly idempotent operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, insert, select, update

from app.api.dependencies import Scope
from app.core.errors import DomainError
from app.db.session import begin_write
from app.models import idempotency_records


def claim(scope: Scope, endpoint: str, key: str, digest: str) -> str | None:
    where = (
        (idempotency_records.c.workspace_id == scope.workspace_id)
        & (idempotency_records.c.endpoint == endpoint)
        & (idempotency_records.c.key == key)
    )
    current = scope.db.execute(select(idempotency_records).where(where)).mappings().first()
    now = datetime.now(UTC)
    if current:
        if current["body_hash"] != digest:
            raise DomainError(
                409, "idempotency_conflict", "This request key belongs to different content."
            )
        if current["state"] == "complete":
            return str(current["response_json"])
        if current["state"] == "pending" and datetime.fromisoformat(current["expires_at"]) > now:
            raise DomainError(
                409, "request_pending", "This request is still running. Retry shortly."
            )
    pending = (
        scope.db.scalar(
            select(func.count())
            .select_from(idempotency_records)
            .where(
                idempotency_records.c.state == "pending",
                idempotency_records.c.expires_at > now.isoformat(),
            )
        )
        or 0
    )
    if pending >= 2:
        raise DomainError(
            429, "provider_busy", "Two generation requests are already running. Retry shortly."
        )
    values = {
        "state": "pending",
        "expires_at": (now + timedelta(seconds=90)).isoformat(),
        "response_json": None,
        "status_code": None,
    }
    if current:
        scope.db.execute(update(idempotency_records).where(where).values(**values))
    else:
        scope.db.execute(
            insert(idempotency_records).values(
                workspace_id=scope.workspace_id,
                endpoint=endpoint,
                key=key,
                body_hash=digest,
                **values,
            )
        )
    return None


def complete(scope: Scope, endpoint: str, key: str, response: str) -> None:
    scope.db.execute(
        update(idempotency_records)
        .where(
            idempotency_records.c.workspace_id == scope.workspace_id,
            idempotency_records.c.endpoint == endpoint,
            idempotency_records.c.key == key,
        )
        .values(
            state="complete",
            response_json=response,
            status_code=200,
            expires_at=(datetime.now(UTC) + timedelta(hours=24)).isoformat(),
        )
    )


def fail(scope: Scope, endpoint: str, key: str) -> None:
    scope.db.rollback()
    begin_write(scope.db)
    scope.db.execute(
        update(idempotency_records)
        .where(
            idempotency_records.c.workspace_id == scope.workspace_id,
            idempotency_records.c.endpoint == endpoint,
            idempotency_records.c.key == key,
        )
        .values(state="failed")
    )
    scope.db.commit()
