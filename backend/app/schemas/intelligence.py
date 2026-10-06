from typing import Literal

from pydantic import Field

from app.schemas.common import StrictModel


class Evidence(StrictModel):
    segment_id: str
    text: str = Field(min_length=1, max_length=2000)


class GeneratedTask(Evidence):
    # Owners and dates are assigned only by deterministic source checks, never model guesses.
    pass


class GeneratedSummary(StrictModel):
    overview: str = Field(min_length=1, max_length=4000)
    key_points: list[Evidence] = Field(max_length=10)
    decisions: list[Evidence] = Field(max_length=10)
    tasks: list[GeneratedTask] = Field(max_length=20)


class RegenerateRequest(StrictModel):
    mode: Literal["extractive", "openai"] = "extractive"
    consent: bool = False


class IntelligenceStatus(StrictModel):
    available: bool
    provider: str
    model: str | None
    context_characters: int
