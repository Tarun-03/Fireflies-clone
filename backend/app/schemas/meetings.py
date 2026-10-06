from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.common import PublicModel, StrictModel
from app.schemas.workspace import Participant, Tag


class SegmentInput(StrictModel):
    speaker: str = Field(min_length=1, max_length=120)
    start_ms: int = Field(ge=0, le=21600000)
    end_ms: int = Field(gt=0, le=21600000)
    text: str = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def times(self) -> "SegmentInput":
        if self.end_ms <= self.start_ms:
            raise ValueError("End must be later than start")
        return self


class PersonInput(StrictModel):
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(None, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class MeetingCreate(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    occurred_at: AwareDatetime
    duration_ms: int = Field(ge=1000, le=21600000)
    source: Literal["pasted", "manual", "uploaded"] = "manual"
    participants: list[PersonInput] = Field(default_factory=list, max_length=100)
    segments: list[SegmentInput] = Field(min_length=1, max_length=3000)
    tag_ids: list[UUID] = Field(default_factory=list, max_length=30)
    estimated_timing: bool = False
    acknowledge_estimated: bool = False

    @model_validator(mode="after")
    def bounds(self) -> "MeetingCreate":
        if max(s.end_ms for s in self.segments) > self.duration_ms:
            raise ValueError("Duration must include every transcript segment")
        if len({s.speaker for s in self.segments}) > 100:
            raise ValueError("At most 100 speakers are supported")
        if sum(len(s.text.encode("utf-8")) for s in self.segments) > 2 * 1024 * 1024:
            raise ValueError("Transcript exceeds the 2 MiB limit")
        if self.estimated_timing and not self.acknowledge_estimated:
            raise ValueError("Acknowledge estimated timing before creating this meeting")
        if len(set(self.tag_ids)) != len(self.tag_ids):
            raise ValueError("Duplicate tags are not allowed")
        return self


class MeetingUpdate(StrictModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    occurred_at: AwareDatetime | None = None
    duration_ms: int | None = Field(None, ge=1000, le=21600000)
    description: str | None = Field(None, max_length=4000)

    @model_validator(mode="after")
    def supplied_values(self) -> "MeetingUpdate":
        for field in ("title", "occurred_at", "duration_ms"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class Meeting(PublicModel):
    id: UUID
    title: str
    occurred_at: str
    duration_ms: int
    source: Literal["seeded", "pasted", "uploaded", "manual"]
    description: str | None
    media_mode: Literal["simulated", "sample"]
    sample_media_key: str | None
    estimated_timing: bool
    transcript_revision: int
    version: int
    participants: list[Participant] = []
    tags: list[Tag] = []


class TagsUpdate(StrictModel):
    tag_ids: list[UUID] = Field(max_length=30)


class AttendeesUpdate(StrictModel):
    participant_ids: list[UUID] = Field(max_length=100)
    removed_task_action: Literal["unassign", "reassign"]
    reassign_to: UUID | None = None


class Speaker(PublicModel):
    id: UUID
    display_name: str
    participant_id: UUID | None
    stable_color_key: int
    version: int


class SpeakerUpdate(StrictModel):
    display_name: str = Field(min_length=1, max_length=120)
    participant_id: UUID | None = None


class TaskInput(StrictModel):
    text: str = Field(min_length=1, max_length=2000)
    assignee_participant_id: UUID | None = None
    due_date: date | None = None


class TaskUpdate(StrictModel):
    text: str | None = Field(None, min_length=1, max_length=2000)
    assignee_participant_id: UUID | None = None
    due_date: date | None = None
    status: Literal["open", "completed"] | None = None

    @model_validator(mode="after")
    def supplied_values(self) -> "TaskUpdate":
        for field in ("text", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class Task(PublicModel):
    id: UUID
    meeting_id: UUID
    text: str
    assignee_participant_id: UUID | None
    due_date: str | None
    status: Literal["open", "completed"]
    completed_at: str | None
    source_segment_id: UUID | None
    origin: Literal["extracted", "manual"]
    source_revision: int | None
    user_edited: bool
    version: int
