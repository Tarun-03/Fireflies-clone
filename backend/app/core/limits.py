import shutil
import threading
import time
from collections import deque
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.models import meetings, segments, workspaces

_lock = threading.Lock()
_requests: dict[tuple[str, str], deque[float]] = {}


def rate_limit(key: str, category: str, limit: int, seconds: int = 60) -> None:
    now = time.monotonic()
    with _lock:
        stale = [k for k, values in _requests.items() if not values or now - values[-1] > 600]
        for expired in stale:
            del _requests[expired]
        bucket = _requests.setdefault((key, category), deque())
        while bucket and now - bucket[0] >= seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise DomainError(429, "rate_limit", "Too many requests. Please wait and try again.")
        bucket.append(now)


def ensure_free_space(added_bytes: int = 3 * 1024 * 1024) -> None:
    config = get_settings()
    if config.remote_database:
        return
    database = Path(config.database_url.removeprefix("sqlite:///"))
    if (
        shutil.disk_usage(database.resolve().parent).free
        < config.disk_reserve_bytes + added_bytes * 4
    ):
        raise DomainError(503, "storage_unavailable", "Storage is temporarily unavailable.")


def check_database_budget(db: Session) -> None:
    if get_settings().remote_database:
        return  # Physical database allocation belongs to Turso; logical quotas remain below.
    pages = int(db.scalar(text("PRAGMA page_count")) or 0)
    free = int(db.scalar(text("PRAGMA freelist_count")) or 0)
    size = int(db.scalar(text("PRAGMA page_size")) or 4096)
    if (pages - free) * size >= get_settings().global_text_bytes:
        raise DomainError(
            429,
            "storage_quota",
            "The demonstration storage limit has been reached. Remove unused c"
            "ontent or contact the operator.",
        )


def check_storage(
    db: Session, workspace_id: str | None = None, added_bytes: int = 0, added_segments: int = 0
) -> None:
    check_database_budget(db)
    config = get_settings()
    ensure_free_space(added_bytes)
    global_bytes = db.scalar(select(func.coalesce(func.sum(func.length(segments.c.text)), 0))) or 0
    # Four bytes per Unicode code point conservatively bounds UTF-8 text storage.
    if global_bytes * 4 + added_bytes > config.global_text_bytes:
        raise DomainError(429, "quota", "The demonstration storage limit has been reached.")
    if workspace_id is None:
        count = db.scalar(select(func.count()).select_from(workspaces)) or 0
        if count >= config.max_workspaces:
            raise DomainError(429, "quota", "The demonstration workspace limit has been reached.")
    else:
        count = (
            db.scalar(
                select(func.count())
                .select_from(meetings)
                .where(meetings.c.workspace_id == workspace_id)
            )
            or 0
        )
        row = db.execute(
            select(func.count(), func.coalesce(func.sum(func.length(segments.c.text)), 0)).where(
                segments.c.workspace_id == workspace_id
            )
        ).one()
        if (
            count >= config.max_meetings
            or row[0] + added_segments > 100000
            or row[1] * 4 + added_bytes > 100 * 1024 * 1024
        ):
            raise DomainError(429, "quota", "Your workspace storage limit has been reached.")
