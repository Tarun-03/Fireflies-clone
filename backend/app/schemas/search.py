from uuid import UUID

from app.schemas.common import PublicModel


class SearchHit(PublicModel):
    id: UUID
    meeting_id: UUID
    segment_id: UUID | None
    title: str
    occurred_at: str
    timestamp_ms: int | None
    speaker_name: str | None
    kind: str
    snippet: str
    ranges: list[tuple[int, int]]
