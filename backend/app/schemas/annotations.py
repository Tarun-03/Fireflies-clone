from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.common import PublicModel, StrictModel

Color = Literal["purple", "blue", "green", "amber", "rose"]


class CommentCreate(StrictModel):
    segment_id: UUID
    segment_version: int = Field(ge=1)
    body: str = Field(min_length=1, max_length=4000)


class CommentUpdate(StrictModel):
    body: str = Field(min_length=1, max_length=4000)


class Comment(PublicModel):
    id: UUID
    meeting_id: UUID
    segment_id: UUID
    body: str
    version: int
    created_at: str


class HighlightCreate(StrictModel):
    segment_id: UUID
    segment_version: int = Field(ge=1)
    start_offset: int = Field(ge=0, le=10000)
    end_offset: int = Field(gt=0, le=10000)
    selected_text: str = Field(min_length=1, max_length=10000)
    note: str = Field("", max_length=4000)
    color: Color = "amber"


class HighlightUpdate(StrictModel):
    note: str = Field(max_length=4000)
    color: Color


class Highlight(PublicModel):
    id: UUID
    meeting_id: UUID
    segment_id: UUID
    start_offset: int
    end_offset: int
    selected_text: str
    note: str
    color: Color
    version: int
    created_at: str


class SoundbiteInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    start_ms: int = Field(ge=0, le=21600000)
    end_ms: int = Field(gt=0, le=21600000)

    @model_validator(mode="after")
    def bounds(self) -> "SoundbiteInput":
        if self.end_ms <= self.start_ms:
            raise ValueError("The end must be after the start")
        return self


class Soundbite(PublicModel):
    id: UUID
    meeting_id: UUID
    title: str
    start_ms: int
    end_ms: int
    version: int
    created_at: str
