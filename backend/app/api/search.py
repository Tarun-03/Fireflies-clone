from datetime import UTC
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import AwareDatetime

from app.api.dependencies import Scoped
from app.schemas.common import Page
from app.schemas.search import SearchHit
from app.services.search import find

router = APIRouter(prefix="/api/v1")


@router.get("/search", response_model=Page[SearchHit])
def search(
    scope: Scoped,
    q: str = Query(min_length=1, max_length=200),
    cursor: int = Query(0, ge=0, le=100000),
    tag: UUID | None = None,
    participant: UUID | None = None,
    kind: Literal["title", "transcript"] | None = None,
    after: AwareDatetime | None = None,
    before: AwareDatetime | None = None,
) -> Page[SearchHit]:
    hits = find(
        scope,
        q,
        offset=cursor,
        limit=26,
        tag=str(tag) if tag else None,
        participant=str(participant) if participant else None,
        kind=kind,
        after=after.astimezone(UTC).isoformat() if after else None,
        before=before.astimezone(UTC).isoformat() if before else None,
    )
    return Page(
        items=hits[:25],
        has_more=len(hits) > 25,
        next_cursor=str(cursor + 25) if len(hits) > 25 else None,
    )
