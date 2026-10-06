from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.dependencies import Scoped
from app.core.errors import DomainError
from app.models import meetings, segments, speakers
from app.repositories.scoped import get_resource
from app.schemas.notebook import Segment, TimelineEntry, Transcript, TranscriptHit, TranscriptSearch

router = APIRouter(prefix="/api/v1/meetings")


def transcript_page(
    scope: Scoped, meeting_id: str, offset: int, limit: int, speaker: UUID | None = None
) -> Transcript:
    meeting = get_resource(scope, meetings, meeting_id)
    query = (
        select(segments, speakers.c.display_name.label("speaker_name"), speakers.c.stable_color_key)
        .join(speakers, speakers.c.id == segments.c.speaker_id)
        .where(segments.c.workspace_id == scope.workspace_id, segments.c.meeting_id == meeting_id)
    )
    if speaker:
        query = query.where(segments.c.speaker_id == str(speaker))
    rows = (
        scope.db.execute(
            query.order_by(segments.c.start_ms, segments.c.ordinal).offset(offset).limit(limit + 1)
        )
        .mappings()
        .all()
    )
    items: list[Segment] = []
    size = 0
    for row in rows[:limit]:
        item = Segment.model_validate(row)
        item_size = len(item.model_dump_json().encode())
        if size + item_size > 512 * 1024 and items:
            break
        items.append(item)
        size += item_size
    more = len(rows) > len(items)
    return Transcript(
        items=items,
        next_cursor=offset + len(items) if more else None,
        has_more=more,
        revision=meeting["transcript_revision"],
        offset=offset,
    )


@router.get("/{meeting_id}/transcript", response_model=Transcript)
def transcript(
    meeting_id: UUID,
    scope: Scoped,
    cursor: int = Query(0, ge=0, le=3000),
    limit: int = Query(60, ge=1, le=100),
    speaker: UUID | None = None,
) -> Transcript:
    return transcript_page(scope, str(meeting_id), cursor, limit, speaker)


@router.get("/{meeting_id}/timeline", response_model=list[TimelineEntry])
def timeline(meeting_id: UUID, scope: Scoped) -> list[TimelineEntry]:
    get_resource(scope, meetings, str(meeting_id))
    return [
        TimelineEntry.model_validate(row)
        for row in scope.db.execute(
            select(segments.c.public_id, segments.c.ordinal, segments.c.start_ms, segments.c.end_ms)
            .where(
                segments.c.workspace_id == scope.workspace_id,
                segments.c.meeting_id == str(meeting_id),
            )
            .order_by(segments.c.start_ms, segments.c.ordinal)
            .limit(3000)
        ).mappings()
    ]


@router.get("/{meeting_id}/transcript/window", response_model=Transcript)
def window(
    meeting_id: UUID,
    scope: Scoped,
    at_ms: int = Query(0, ge=0, le=21600000),
    segment_id: UUID | None = None,
) -> Transcript:
    index = timeline(meeting_id, scope)
    position = 0
    if segment_id:
        matches = [i for i, item in enumerate(index) if item.public_id == segment_id]
        if not matches:
            raise DomainError(404, "not_found", "This transcript segment is no longer available.")
        position = matches[0]
    else:
        for i, item in enumerate(index):
            if item.start_ms <= at_ms:
                position = i
            else:
                break
    return transcript_page(scope, str(meeting_id), max(0, position - 15), 60)


@router.get("/{meeting_id}/transcript/search", response_model=TranscriptSearch)
def search(
    meeting_id: UUID,
    scope: Scoped,
    q: str = Query(min_length=1, max_length=200),
    speaker: UUID | None = None,
    cursor: int = Query(0, ge=0, le=3000),
) -> TranscriptSearch:
    get_resource(scope, meetings, str(meeting_id))
    # Literal Unicode matching avoids exposing SQL/FTS grammar and preserves code-point ranges.
    query = (
        select(segments.c.public_id, segments.c.start_ms, segments.c.text, speakers.c.display_name)
        .join(speakers, speakers.c.id == segments.c.speaker_id)
        .where(
            segments.c.workspace_id == scope.workspace_id, segments.c.meeting_id == str(meeting_id)
        )
    )
    if speaker:
        query = query.where(segments.c.speaker_id == str(speaker))
    hits: list[TranscriptHit] = []
    import re

    pattern = re.compile(re.escape(q), re.IGNORECASE)
    for row in scope.db.execute(
        query.order_by(segments.c.start_ms, segments.c.ordinal).limit(3000)
    ).mappings():
        match = pattern.search(row["text"])
        if match:
            start = max(0, match.start() - 60)
            snippet = row["text"][start : start + 260]
            ranges = [(m.start(), m.end()) for m in pattern.finditer(snippet)]
            hits.append(
                TranscriptHit(
                    segment_id=row["public_id"],
                    timestamp_ms=row["start_ms"],
                    speaker_name=row["display_name"],
                    snippet=snippet,
                    ranges=ranges,
                )
            )
    return TranscriptSearch(
        items=hits[cursor : cursor + 100],
        total=len(hits),
        next_cursor=cursor + 100 if len(hits) > cursor + 100 else None,
    )
