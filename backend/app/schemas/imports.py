from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.common import StrictModel
from app.schemas.meetings import PersonInput, SegmentInput


class ImportRequest(StrictModel):
    format: Literal["txt", "vtt", "json"]
    filename: str | None = Field(None, max_length=128)
    content: str | None = Field(None, max_length=2097152)
    content_base64: str | None = Field(None, max_length=2796204)
    title: str | None = Field(None, min_length=1, max_length=200)
    occurred_at: AwareDatetime | None = None
    participants: list[PersonInput] | None = Field(None, max_length=100)
    tag_ids: list[UUID] = Field(default_factory=list, max_length=30)
    acknowledge_estimated: bool = False

    @model_validator(mode="after")
    def one_content(self) -> "ImportRequest":
        if (self.content is None) == (self.content_base64 is None):
            raise ValueError("Provide exactly one transcript or file")
        return self


class ParsedTranscript(StrictModel):
    title: str | None = None
    occurred_at: datetime | None = None
    participants: list[PersonInput] = Field(default_factory=list)
    segments: list[SegmentInput]
    duration_ms: int
    estimated_timing: bool = False
    warnings: list[str] = Field(default_factory=list)


class ImportPreview(StrictModel):
    title: str | None
    occurred_at: datetime | None
    participants: list[PersonInput]
    segments: list[SegmentInput]
    segment_count: int
    duration_ms: int
    estimated_timing: bool
    warnings: list[str]
