from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from app.schemas.common import PublicModel, StrictModel


class Preferences(PublicModel):
    theme: Literal["light", "dark", "system"]
    timezone: str
    player_speed: float
    reduced_motion: bool
    version: int


class PreferencesUpdate(StrictModel):
    theme: Literal["light", "dark", "system"] | None = None
    timezone: str | None = Field(None, max_length=80)
    player_speed: float | None = None
    reduced_motion: bool | None = None

    @field_validator("player_speed")
    @classmethod
    def valid_speed(cls, value: float | None) -> float | None:
        if value is not None and value not in {0.5, 0.75, 1, 1.25, 1.5, 2}:
            raise ValueError("Choose an available playback speed")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except ZoneInfoNotFoundError as exc:
                raise ValueError("Choose a valid IANA timezone") from exc
        return value


class Profile(PublicModel):
    id: UUID
    display_name: str
    workspace_name: str
    preferences: Preferences
    ai_available: bool


class TagInput(StrictModel):
    name: str = Field(min_length=1, max_length=60)
    color: Literal["purple", "blue", "green", "amber", "rose", "gray"] = "purple"


class Tag(PublicModel):
    name: str
    color: str
    id: UUID
    version: int


class Participant(PublicModel):
    id: UUID
    display_name: str
    normalized_email: str | None
    version: int


class ParticipantUpdate(StrictModel):
    display_name: str = Field(min_length=1, max_length=120)


class Activity(PublicModel):
    id: UUID
    meeting_id: UUID | None
    kind: str
    text: str
    is_read: bool
    created_at: str
    version: int


class ActivityUpdate(StrictModel):
    is_read: bool


class SessionResult(PublicModel):
    ready: bool = True
