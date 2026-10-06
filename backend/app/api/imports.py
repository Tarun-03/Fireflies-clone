import hashlib
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header

from app.api.dependencies import Scoped
from app.core.errors import DomainError
from app.schemas.imports import ImportPreview, ImportRequest
from app.schemas.meetings import Meeting, MeetingCreate
from app.services.creation import create_meeting
from app.services.parsers import parse

router = APIRouter(prefix="/api/v1/meetings/import")


@router.post("/preview", response_model=ImportPreview)
def preview(data: ImportRequest, scope: Scoped) -> ImportPreview:
    parsed = parse(data)
    return ImportPreview(
        **parsed.model_dump(exclude={"segments"}),
        segments=parsed.segments[:10],
        segment_count=len(parsed.segments),
    )


@router.post("", response_model=Meeting, status_code=201)
def import_meeting(
    data: ImportRequest, scope: Scoped, idempotency_key: Annotated[UUID, Header()]
) -> Meeting:
    parsed = parse(data)
    if parsed.estimated_timing and not data.acknowledge_estimated:
        raise DomainError(
            422, "acknowledgement_required", "Acknowledge estimated timing before importing."
        )
    meeting = MeetingCreate(
        title=data.title or parsed.title or "Imported meeting",
        occurred_at=data.occurred_at or parsed.occurred_at or datetime.now(UTC),
        duration_ms=parsed.duration_ms,
        participants=data.participants if data.participants is not None else parsed.participants,
        segments=parsed.segments,
        tag_ids=data.tag_ids,
        source="uploaded" if data.filename else "pasted",
        estimated_timing=parsed.estimated_timing,
        acknowledge_estimated=data.acknowledge_estimated,
    )
    return create_meeting(
        scope,
        meeting,
        str(idempotency_key),
        hashlib.sha256(data.model_dump_json().encode()).hexdigest(),
    )
