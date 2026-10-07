import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, insert, select

from app.api.dependencies import Scope
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.limits import check_storage, rate_limit
from app.db.bulk import insert_rows
from app.models import (
    action_items,
    attendees,
    chapters,
    idempotency_records,
    meeting_tags,
    meetings,
    participants,
    segments,
    speakers,
    summaries,
    summary_points,
    tags,
)
from app.models.common import now, uid
from app.repositories.meetings import meeting_details
from app.repositories.scoped import get_resource
from app.schemas.meetings import Meeting, MeetingCreate
from app.services.activity import record_activity
from app.services.maintenance import expire_key


def create_meeting(
    scope: Scope, data: MeetingCreate, key: str, request_hash: str | None = None
) -> Meeting:
    expire_key(scope.db, scope.workspace_id, "create-meeting", key)
    digest = request_hash or hashlib.sha256(data.model_dump_json().encode()).hexdigest()
    existing = (
        scope.db.execute(
            select(idempotency_records).where(
                idempotency_records.c.workspace_id == scope.workspace_id,
                idempotency_records.c.key == key,
                idempotency_records.c.endpoint == "create-meeting",
            )
        )
        .mappings()
        .first()
    )
    if existing:
        if existing["body_hash"] != digest:
            raise DomainError(
                409, "idempotency_conflict", "This request key was used for different content."
            )
        if existing["state"] != "complete":
            raise DomainError(
                409, "request_pending", "This request has not completed. Please retry later."
            )
        return Meeting.model_validate_json(existing["response_json"])
    rate_limit(scope.session_id, "imports", get_settings().imports_per_ten_minutes, 600)
    check_storage(
        scope.db,
        scope.workspace_id,
        sum(len(segment.text.encode()) for segment in data.segments),
        len(data.segments),
    )
    for tag_id in data.tag_ids:
        get_resource(scope, tags, str(tag_id))
    meeting_id = uid()
    context = dict(workspace_id=scope.workspace_id, meeting_id=meeting_id)
    scope.db.execute(
        insert(meetings).values(
            id=meeting_id,
            workspace_id=scope.workspace_id,
            created_by_id=scope.user_id,
            title=data.title,
            occurred_at=data.occurred_at.astimezone(UTC).isoformat(),
            duration_ms=data.duration_ms,
            source=data.source,
            estimated_timing=int(data.estimated_timing),
        )
    )
    local_people: dict[str, list[str]] = {}
    for person in data.participants:
        person_id = None
        if person.email:
            person_id = scope.db.scalar(
                select(participants.c.id).where(
                    participants.c.workspace_id == scope.workspace_id,
                    participants.c.normalized_email == person.email.casefold(),
                )
            )
        if person_id is None:
            person_id = uid()
            scope.db.execute(
                insert(participants).values(
                    id=person_id,
                    workspace_id=scope.workspace_id,
                    display_name=person.display_name,
                    normalized_email=person.email.casefold() if person.email else None,
                )
            )
        local_people.setdefault(person.display_name, []).append(person_id)
        present = scope.db.scalar(
            select(attendees.c.participant_id).where(
                attendees.c.meeting_id == meeting_id, attendees.c.participant_id == person_id
            )
        )
        if present is None:
            scope.db.execute(insert(attendees).values(**context, participant_id=person_id))
    people_count = (
        scope.db.scalar(
            select(func.count())
            .select_from(participants)
            .where(participants.c.workspace_id == scope.workspace_id)
        )
        or 0
    )
    if people_count > 500:
        raise DomainError(
            429,
            "participant_quota",
            "This workspace supports up to 500 participants. Reuse an existing email identity.",
        )
    speaker_ids: dict[str, str] = {}
    source_ids: list[str] = []
    segment_rows: list[dict[str, Any]] = []
    for ordinal, segment in enumerate(data.segments):
        if segment.speaker not in speaker_ids:
            speaker_ids[segment.speaker] = uid()
            candidates = local_people.get(segment.speaker, [])
            scope.db.execute(
                insert(speakers).values(
                    **context,
                    id=speaker_ids[segment.speaker],
                    display_name=segment.speaker,
                    participant_id=candidates[0] if len(candidates) == 1 else None,
                    stable_color_key=(len(speaker_ids) - 1) % 8,
                    position=len(speaker_ids) - 1,
                )
            )
        source_id = uid()
        source_ids.append(source_id)
        segment_rows.append(
            dict(
                **context,
                public_id=source_id,
                ordinal=ordinal,
                speaker_id=speaker_ids[segment.speaker],
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                text=segment.text,
            )
        )
    insert_rows(scope.db, segments, segment_rows)
    summary_id = uid()
    scope.db.execute(
        insert(summaries).values(
            **context,
            id=summary_id,
            overview=" ".join(segment.text[:400] for segment in data.segments[:3]),
            provider="extractive",
            source_revision=1,
            generated_at=now(),
        )
    )
    tasks_seen: set[str] = set()
    point_count = 0
    for index, segment in enumerate(data.segments):
        if point_count < 30 and (index < 5 or "we decided" in segment.text.casefold()):
            point_count += 1
            scope.db.execute(
                insert(summary_points).values(
                    **context,
                    summary_id=summary_id,
                    kind="decision" if "we decided" in segment.text.casefold() else "key_point",
                    text=segment.text[:2000],
                    position=index,
                    source_segment_id=source_ids[index],
                )
            )
        if (
            "i will " in segment.text.casefold()
            and segment.text not in tasks_seen
            and len(tasks_seen) < 30
        ):
            tasks_seen.add(segment.text)
            candidates = local_people.get(segment.speaker, [])
            scope.db.execute(
                insert(action_items).values(
                    **context,
                    text=segment.text[:2000],
                    assignee_participant_id=candidates[0] if len(candidates) == 1 else None,
                    source_segment_id=source_ids[index],
                    origin="extracted",
                    source_revision=1,
                )
            )
    chunk = max(1, (len(data.segments) + 5) // 6)
    for position, start in enumerate(range(0, len(data.segments), chunk)):
        group = data.segments[start : start + chunk]
        scope.db.execute(
            insert(chapters).values(
                **context,
                title=group[0].text[:80],
                description=group[0].text[:500],
                start_ms=min(s.start_ms for s in group),
                end_ms=max(s.end_ms for s in group),
                position=position,
                source_revision=1,
            )
        )
    for tag_id in data.tag_ids:
        scope.db.execute(insert(meeting_tags).values(**context, tag_id=str(tag_id)))
    record_activity(scope, "meeting.created", "A meeting was created", meeting_id)
    result = meeting_details(scope, [meeting_id])[0]
    scope.db.execute(
        insert(idempotency_records).values(
            workspace_id=scope.workspace_id,
            key=key,
            endpoint="create-meeting",
            body_hash=digest,
            state="complete",
            status_code=201,
            response_json=result.model_dump_json(),
            expires_at=(datetime.now(UTC) + timedelta(hours=24)).isoformat(),
        )
    )
    return result
