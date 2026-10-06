import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError
from sqlalchemy import and_, or_, select

from app.api.dependencies import Scope
from app.core.errors import DomainError
from app.models import attendees, meeting_tags, meetings, participants, tags
from app.schemas.common import Page, StrictModel
from app.schemas.meetings import Meeting
from app.schemas.workspace import Participant, Tag


class Cursor(StrictModel):
    value: str
    id: str
    fingerprint: str


@dataclass
class Filters:
    q: str = ""
    participant: str | None = None
    tag: str | None = None
    after: str | None = None
    before: str | None = None
    minimum: int | None = None
    maximum: int | None = None
    source: str | None = None
    sort: Literal["recent", "oldest", "title"] = "recent"


def meeting_details(scope: Scope, ids: list[str]) -> list[Meeting]:
    if not ids:
        return []
    people: dict[str, list[Participant]] = {key: [] for key in ids}
    labels: dict[str, list[Tag]] = {key: [] for key in ids}
    for row in scope.db.execute(
        select(participants, attendees.c.meeting_id)
        .join(attendees, attendees.c.participant_id == participants.c.id)
        .where(attendees.c.workspace_id == scope.workspace_id, attendees.c.meeting_id.in_(ids))
    ).mappings():
        people[row["meeting_id"]].append(Participant.model_validate(row))
    for row in scope.db.execute(
        select(tags, meeting_tags.c.meeting_id)
        .join(meeting_tags, meeting_tags.c.tag_id == tags.c.id)
        .where(
            meeting_tags.c.workspace_id == scope.workspace_id, meeting_tags.c.meeting_id.in_(ids)
        )
    ).mappings():
        labels[row["meeting_id"]].append(Tag.model_validate(row))
    by_id = {
        row["id"]: Meeting.model_validate(
            dict(row) | {"participants": people[row["id"]], "tags": labels[row["id"]]}
        )
        for row in scope.db.execute(
            select(meetings).where(
                meetings.c.workspace_id == scope.workspace_id, meetings.c.id.in_(ids)
            )
        ).mappings()
    }
    return [by_id[key] for key in ids if key in by_id]


def library(scope: Scope, filters: Filters, limit: int, cursor: str | None) -> Page[Meeting]:
    applied = vars(filters)
    fingerprint = hashlib.sha256(json.dumps(applied, sort_keys=True).encode()).hexdigest()
    query = select(meetings.c.id, meetings.c.occurred_at, meetings.c.title).where(
        meetings.c.workspace_id == scope.workspace_id
    )
    if filters.q:
        query = query.where(meetings.c.title.icontains(filters.q, autoescape=True))
    if filters.participant:
        query = query.where(
            meetings.c.id.in_(
                select(attendees.c.meeting_id).where(
                    attendees.c.participant_id == filters.participant,
                    attendees.c.workspace_id == scope.workspace_id,
                )
            )
        )
    if filters.tag:
        query = query.where(
            meetings.c.id.in_(
                select(meeting_tags.c.meeting_id).where(
                    meeting_tags.c.tag_id == filters.tag,
                    meeting_tags.c.workspace_id == scope.workspace_id,
                )
            )
        )
    if filters.after:
        query = query.where(meetings.c.occurred_at >= filters.after)
    if filters.before:
        query = query.where(meetings.c.occurred_at < filters.before)
    if filters.minimum is not None:
        query = query.where(meetings.c.duration_ms >= filters.minimum)
    if filters.maximum is not None:
        query = query.where(meetings.c.duration_ms < filters.maximum)
    if filters.source:
        query = query.where(meetings.c.source == filters.source)
    column = meetings.c.title if filters.sort == "title" else meetings.c.occurred_at
    descending = filters.sort == "recent"
    if cursor:
        try:
            marker = Cursor.model_validate_json(base64.urlsafe_b64decode(cursor.encode()))
            if marker.fingerprint != fingerprint:
                raise ValueError()
        except (ValueError, ValidationError) as exc:
            raise DomainError(
                422, "invalid_cursor", "These filters changed. Return to the first page."
            ) from exc
        comparison = column < marker.value if descending else column > marker.value
        tie = meetings.c.id < marker.id if descending else meetings.c.id > marker.id
        query = query.where(or_(comparison, and_(column == marker.value, tie)))
    rows = (
        scope.db.execute(
            query.order_by(
                column.desc() if descending else column.asc(),
                meetings.c.id.desc() if descending else meetings.c.id.asc(),
            ).limit(limit + 1)
        )
        .mappings()
        .all()
    )
    more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = None
    if more:
        last = rows[-1]
        value = last["title"] if filters.sort == "title" else last["occurred_at"]
        next_cursor = base64.urlsafe_b64encode(
            Cursor(value=value, id=last["id"], fingerprint=fingerprint).model_dump_json().encode()
        ).decode()
    return Page(
        items=meeting_details(scope, [row["id"] for row in rows]),
        has_more=more,
        next_cursor=next_cursor,
        applied_filters=applied,
    )
