from uuid import UUID

from fastapi import APIRouter
from pydantic import Field, model_validator
from sqlalchemy import LargeBinary, cast, delete, func, select, update

from app.api.dependencies import Scoped, Version, require_version
from app.core.errors import DomainError
from app.models import chat_citations, comments, highlights, meetings, segments, speakers
from app.repositories.scoped import get_resource
from app.schemas.common import StrictModel
from app.schemas.notebook import Segment

router = APIRouter(prefix="/api/v1/meetings")


class SegmentUpdate(StrictModel):
    text: str = Field(min_length=1, max_length=10000)
    start_ms: int = Field(ge=0, le=21600000)
    end_ms: int = Field(gt=0, le=21600000)
    remove_affected_highlights: bool = False

    @model_validator(mode="after")
    def bounds(self) -> "SegmentUpdate":
        if self.end_ms <= self.start_ms or not self.text.strip():
            raise ValueError("Provide nonempty text and an end time after the start")
        return self


class SegmentImpact(StrictModel):
    highlights: int
    comments: int
    citations: int


def scoped_segment(scope: Scoped, meeting_id: UUID, segment_id: UUID) -> Segment:
    row = (
        scope.db.execute(
            select(
                segments, speakers.c.display_name.label("speaker_name"), speakers.c.stable_color_key
            )
            .join(speakers, speakers.c.id == segments.c.speaker_id)
            .where(
                segments.c.workspace_id == scope.workspace_id,
                segments.c.meeting_id == str(meeting_id),
                segments.c.public_id == str(segment_id),
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        raise DomainError(404, "not_found", "This transcript turn is no longer available.")
    return Segment.model_validate(row)


def revised(scope: Scoped, meeting_id: UUID) -> None:
    scope.db.execute(
        update(meetings)
        .where(meetings.c.id == str(meeting_id), meetings.c.workspace_id == scope.workspace_id)
        .values(
            transcript_revision=meetings.c.transcript_revision + 1, version=meetings.c.version + 1
        )
    )


@router.get("/{meeting_id}/segments/{segment_id}/impact", response_model=SegmentImpact)
def impact(meeting_id: UUID, segment_id: UUID, scope: Scoped) -> SegmentImpact:
    scoped_segment(scope, meeting_id, segment_id)
    counts = {}
    for name, table in [
        ("highlights", highlights),
        ("comments", comments),
        ("citations", chat_citations),
    ]:
        counts[name] = (
            scope.db.scalar(
                select(func.count())
                .select_from(table)
                .where(
                    table.c.workspace_id == scope.workspace_id,
                    table.c.meeting_id == str(meeting_id),
                    table.c.segment_id == str(segment_id),
                )
            )
            or 0
        )
    return SegmentImpact(**counts)


@router.patch("/{meeting_id}/segments/{segment_id}", response_model=Segment)
def edit(
    meeting_id: UUID, segment_id: UUID, data: SegmentUpdate, scope: Scoped, if_match: Version = None
) -> Segment:
    current = scoped_segment(scope, meeting_id, segment_id)
    require_version(current.version, if_match)
    meeting = get_resource(scope, meetings, str(meeting_id))
    if data.end_ms > meeting["duration_ms"]:
        raise DomainError(422, "invalid_time", "The end must be within the meeting duration.")
    size = (
        scope.db.scalar(
            select(func.sum(func.length(cast(segments.c.text, LargeBinary)))).where(
                segments.c.meeting_id == str(meeting_id)
            )
        )
        or 0
    )
    if size - len(current.text.encode()) + len(data.text.encode()) > 2 * 1024 * 1024:
        raise DomainError(429, "text_quota", "This edit exceeds the meeting text allowance.")
    if data.text != current.text:
        affected = impact(meeting_id, segment_id, scope)
        if affected.highlights and not data.remove_affected_highlights:
            raise DomainError(
                409,
                "annotations_affected",
                "Text changes remove this turn’s highlights. Acknowledge this before saving.",
            )
        scope.db.execute(
            delete(highlights).where(
                highlights.c.segment_id == str(segment_id),
                highlights.c.workspace_id == scope.workspace_id,
            )
        )
        scope.db.execute(
            update(chat_citations)
            .where(
                chat_citations.c.segment_id == str(segment_id),
                chat_citations.c.workspace_id == scope.workspace_id,
            )
            .values(segment_id=None)
        )
    scope.db.execute(
        update(segments)
        .where(
            segments.c.public_id == str(segment_id), segments.c.workspace_id == scope.workspace_id
        )
        .values(
            text=data.text, start_ms=data.start_ms, end_ms=data.end_ms, version=current.version + 1
        )
    )
    revised(scope, meeting_id)
    return scoped_segment(scope, meeting_id, segment_id)


@router.delete("/{meeting_id}/segments/{segment_id}", status_code=204)
def remove(meeting_id: UUID, segment_id: UUID, scope: Scoped, if_match: Version = None) -> None:
    current = scoped_segment(scope, meeting_id, segment_id)
    require_version(current.version, if_match)
    scope.db.execute(
        delete(segments).where(
            segments.c.public_id == str(segment_id), segments.c.workspace_id == scope.workspace_id
        )
    )
    revised(scope, meeting_id)
