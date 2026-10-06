from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import PublicModel, StrictModel


class ChatRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    mode: Literal["extractive", "openai"] = "extractive"
    consent: bool = False


class GeneratedAnswer(StrictModel):
    answer: str = Field(min_length=1, max_length=6000)
    supported: bool
    citations: list[str] = Field(max_length=12)


class Citation(PublicModel):
    segment_id: UUID | None
    original_segment_public_id: UUID
    timestamp_ms: int
    source_revision: int


class ChatMessage(PublicModel):
    id: UUID
    role: str
    content: str
    provider: str | None
    model: str | None
    source_revision: int
    created_at: str
    citations: list[Citation] = Field(default_factory=list)


class ChatHistory(PublicModel):
    items: list[ChatMessage]
    has_more: bool
    next_cursor: int | None
    version: int
    transcript_revision: int


class ChatResult(PublicModel):
    user: ChatMessage
    assistant: ChatMessage
    notice: str | None
