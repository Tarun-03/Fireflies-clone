from uuid import UUID

from pydantic import Field

from app.schemas.common import PublicModel, StrictModel


class Segment(PublicModel):
    public_id: UUID
    speaker_id: UUID
    ordinal: int
    start_ms: int
    end_ms: int
    text: str
    version: int
    speaker_name: str
    stable_color_key: int


class Transcript(PublicModel):
    items: list[Segment]
    next_cursor: int | None
    has_more: bool
    revision: int
    offset: int


class TimelineEntry(PublicModel):
    public_id: UUID
    ordinal: int
    start_ms: int
    end_ms: int


class TranscriptHit(PublicModel):
    segment_id: UUID
    timestamp_ms: int
    speaker_name: str
    snippet: str
    ranges: list[tuple[int, int]]


class TranscriptSearch(PublicModel):
    items: list[TranscriptHit]
    total: int
    next_cursor: int | None


class SummaryPoint(PublicModel):
    id: UUID
    kind: str
    text: str
    source_segment_id: UUID | None


class Summary(PublicModel):
    id: UUID
    overview: str
    notes: str
    provider: str
    model: str | None
    source_revision: int
    generated_at: str
    version: int
    stale: bool
    points: list[SummaryPoint]
    notice: str | None = None


class NotesUpdate(StrictModel):
    notes: str = Field(max_length=20000)


class Chapter(PublicModel):
    id: UUID
    title: str
    description: str
    start_ms: int
    end_ms: int
    source_revision: int
