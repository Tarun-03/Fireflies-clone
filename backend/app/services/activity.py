from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, insert, select

from app.api.dependencies import Scope
from app.models import activity_events


def record_activity(
    scope: Scope, kind: str, display_text: str, meeting_id: str | None = None
) -> None:
    scope.db.execute(
        insert(activity_events).values(
            workspace_id=scope.workspace_id,
            actor_id=scope.user_id,
            meeting_id=meeting_id,
            kind=kind,
            text=display_text[:250],
        )
    )
    cutoff = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    scope.db.execute(
        delete(activity_events).where(
            activity_events.c.workspace_id == scope.workspace_id,
            activity_events.c.created_at < cutoff,
        )
    )
    keep = (
        select(activity_events.c.id)
        .where(activity_events.c.workspace_id == scope.workspace_id)
        .order_by(activity_events.c.created_at.desc(), activity_events.c.id.desc())
        .limit(1000)
    )
    scope.db.execute(
        delete(activity_events).where(
            activity_events.c.workspace_id == scope.workspace_id, activity_events.c.id.not_in(keep)
        )
    )
