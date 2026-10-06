"""Bounded cleanup of expired anonymous data, always inside a writer transaction."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import demo_sessions, idempotency_records, memberships, users, workspaces


def prune_expired(
    db: Session,
    maximum: int = 10,
    *,
    apply: bool = False,
    expired_workspaces: bool = False,
    retention_days: int = 7,
) -> int:
    cutoff = datetime.now(UTC).isoformat()
    retained = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()
    expired = db.execute(
        select(demo_sessions.c.workspace_id, demo_sessions.c.user_id)
        .where(demo_sessions.c.expires_at < retained)
        .order_by(demo_sessions.c.expires_at)
        .limit(maximum)
    ).all()
    if not apply:
        return len(expired) if expired_workspaces else 0
    for workspace_id, user_id in expired if expired_workspaces else []:
        db.execute(delete(workspaces).where(workspaces.c.id == workspace_id))
        if db.scalar(select(memberships.c.user_id).where(memberships.c.user_id == user_id)) is None:
            db.execute(delete(users).where(users.c.id == user_id))
    db.execute(delete(idempotency_records).where(idempotency_records.c.expires_at < cutoff))
    return len(expired) if expired_workspaces else 0


def expire_key(db: Session, workspace_id: str, endpoint: str, key: str) -> None:
    db.execute(
        delete(idempotency_records).where(
            idempotency_records.c.workspace_id == workspace_id,
            idempotency_records.c.endpoint == endpoint,
            idempotency_records.c.key == key,
            idempotency_records.c.expires_at < datetime.now(UTC).isoformat(),
        )
    )
