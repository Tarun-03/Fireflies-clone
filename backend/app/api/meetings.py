from datetime import UTC
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query
from pydantic import AwareDatetime
from sqlalchemy import delete, insert, select, update

from app.api.dependencies import Scoped, Version, require_version
from app.core.errors import DomainError
from app.models import action_items, attendees, meeting_tags, meetings, participants, speakers, tags
from app.repositories.meetings import Filters, library, meeting_details
from app.repositories.scoped import get_resource
from app.schemas.common import Page
from app.schemas.meetings import (
    AttendeesUpdate,
    Meeting,
    MeetingCreate,
    MeetingUpdate,
    Speaker,
    SpeakerUpdate,
    TagsUpdate,
)
from app.services.activity import record_activity
from app.services.creation import create_meeting

router = APIRouter(prefix="/api/v1/meetings")


@router.get("", response_model=Page[Meeting])
def list_meetings(
    scope: Scoped,
    q: str = Query("", max_length=200),
    participant: UUID | None = None,
    tag: UUID | None = None,
    after: AwareDatetime | None = None,
    before: AwareDatetime | None = None,
    minimum: int | None = Query(None, ge=0, le=21600000),
    maximum: int | None = Query(None, ge=0, le=21600000),
    source: Literal["seeded", "pasted", "uploaded", "manual"] | None = None,
    sort: Literal["recent", "oldest", "title"] = "recent",
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, max_length=1000),
) -> Page[Meeting]:
    return library(
        scope,
        Filters(
            q,
            str(participant) if participant else None,
            str(tag) if tag else None,
            after.astimezone(UTC).isoformat() if after else None,
            before.astimezone(UTC).isoformat() if before else None,
            minimum,
            maximum,
            source,
            sort,
        ),
        limit,
        cursor,
    )


@router.post("", response_model=Meeting, status_code=201)
def create(
    data: MeetingCreate,
    scope: Scoped,
    idempotency_key: Annotated[str, Header(min_length=16, max_length=100)],
) -> Meeting:
    return create_meeting(scope, data, idempotency_key)


@router.get("/{meeting_id}", response_model=Meeting)
def detail(meeting_id: UUID, scope: Scoped) -> Meeting:
    get_resource(scope, meetings, str(meeting_id))
    return meeting_details(scope, [str(meeting_id)])[0]


@router.patch("/{meeting_id}", response_model=Meeting)
def edit(meeting_id: UUID, data: MeetingUpdate, scope: Scoped, if_match: Version = None) -> Meeting:
    row = get_resource(scope, meetings, str(meeting_id))
    require_version(row["version"], if_match)
    values = data.model_dump(exclude_none=True)
    if data.occurred_at:
        values["occurred_at"] = data.occurred_at.astimezone(UTC).isoformat()
    scope.db.execute(
        update(meetings)
        .where(meetings.c.id == str(meeting_id))
        .values(**values, version=row["version"] + 1)
    )
    record_activity(scope, "meeting.updated", "Meeting details were updated", str(meeting_id))
    return detail(meeting_id, scope)


@router.delete("/{meeting_id}", status_code=204)
def remove(meeting_id: UUID, scope: Scoped, if_match: Version = None) -> None:
    row = get_resource(scope, meetings, str(meeting_id))
    require_version(row["version"], if_match)
    scope.db.execute(delete(meetings).where(meetings.c.id == str(meeting_id)))
    record_activity(scope, "meeting.deleted", "A meeting was deleted")


@router.put("/{meeting_id}/tags", response_model=Meeting)
def set_tags(
    meeting_id: UUID, data: TagsUpdate, scope: Scoped, if_match: Version = None
) -> Meeting:
    row = get_resource(scope, meetings, str(meeting_id))
    require_version(row["version"], if_match)
    for tag_id in data.tag_ids:
        get_resource(scope, tags, str(tag_id))
    scope.db.execute(delete(meeting_tags).where(meeting_tags.c.meeting_id == str(meeting_id)))
    for tag_id in set(data.tag_ids):
        scope.db.execute(
            insert(meeting_tags).values(
                workspace_id=scope.workspace_id, meeting_id=str(meeting_id), tag_id=str(tag_id)
            )
        )
    scope.db.execute(
        update(meetings).where(meetings.c.id == str(meeting_id)).values(version=row["version"] + 1)
    )
    return detail(meeting_id, scope)


@router.put("/{meeting_id}/participants", response_model=Meeting)
def set_attendees(
    meeting_id: UUID, data: AttendeesUpdate, scope: Scoped, if_match: Version = None
) -> Meeting:
    row = get_resource(scope, meetings, str(meeting_id))
    require_version(row["version"], if_match)
    wanted = {str(key) for key in data.participant_ids}
    for person in wanted:
        get_resource(scope, participants, person)
    if data.removed_task_action == "reassign" and (
        data.reassign_to is None or str(data.reassign_to) not in wanted
    ):
        raise DomainError(422, "invalid_assignee", "Choose an attendee to receive these tasks.")
    current = set(
        scope.db.scalars(
            select(attendees.c.participant_id).where(attendees.c.meeting_id == str(meeting_id))
        )
    )
    for person in wanted - current:
        scope.db.execute(
            insert(attendees).values(
                workspace_id=scope.workspace_id, meeting_id=str(meeting_id), participant_id=person
            )
        )
    removed = current - wanted
    scope.db.execute(
        update(action_items)
        .where(
            action_items.c.meeting_id == str(meeting_id),
            action_items.c.assignee_participant_id.in_(removed),
        )
        .values(
            assignee_participant_id=str(data.reassign_to)
            if data.removed_task_action == "reassign"
            else None,
            user_edited=True,
            version=action_items.c.version + 1,
        )
    )
    scope.db.execute(
        delete(attendees).where(
            attendees.c.meeting_id == str(meeting_id), attendees.c.participant_id.in_(removed)
        )
    )
    scope.db.execute(
        update(meetings).where(meetings.c.id == str(meeting_id)).values(version=row["version"] + 1)
    )
    return detail(meeting_id, scope)


@router.get("/{meeting_id}/speakers", response_model=list[Speaker])
def list_speakers(meeting_id: UUID, scope: Scoped) -> list[Speaker]:
    get_resource(scope, meetings, str(meeting_id))
    return [
        Speaker.model_validate(row)
        for row in scope.db.execute(
            select(speakers)
            .where(
                speakers.c.meeting_id == str(meeting_id),
                speakers.c.workspace_id == scope.workspace_id,
            )
            .order_by(speakers.c.position)
        ).mappings()
    ]


@router.patch("/{meeting_id}/speakers/{speaker_id}", response_model=Speaker)
def edit_speaker(
    meeting_id: UUID, speaker_id: UUID, data: SpeakerUpdate, scope: Scoped, if_match: Version = None
) -> Speaker:
    row = get_resource(scope, speakers, str(speaker_id), str(meeting_id))
    require_version(row["version"], if_match)
    if data.participant_id:
        get_resource(scope, participants, str(data.participant_id))
    scope.db.execute(
        update(speakers)
        .where(speakers.c.id == str(speaker_id))
        .values(
            display_name=data.display_name,
            participant_id=str(data.participant_id) if data.participant_id else None,
            version=row["version"] + 1,
        )
    )
    scope.db.execute(
        update(meetings)
        .where(meetings.c.id == str(meeting_id))
        .values(
            transcript_revision=meetings.c.transcript_revision + 1, version=meetings.c.version + 1
        )
    )
    return Speaker.model_validate(get_resource(scope, speakers, str(speaker_id), str(meeting_id)))
