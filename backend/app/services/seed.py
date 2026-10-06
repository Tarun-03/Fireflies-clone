"""Clone versioned synthetic fixtures once, inside the caller's write transaction."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.models import (
    action_items,
    activity_events,
    attendees,
    chapters,
    demo_sessions,
    meeting_tags,
    meetings,
    memberships,
    participants,
    preferences,
    segments,
    speakers,
    summaries,
    summary_points,
    tags,
    users,
    workspaces,
)
from app.models.common import now, uid


class FixtureModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Person(FixtureModel):
    display_name: str
    email: str


class SeedSegment(FixtureModel):
    speaker: str
    start_ms: int
    end_ms: int
    text: str


class SeedChapter(FixtureModel):
    title: str
    description: str
    start_ms: int
    end_ms: int
    position: int


class SeedTask(FixtureModel):
    text: str
    segment_ordinal: int
    owner: str
    status: str


class SeedPoint(FixtureModel):
    kind: str
    text: str
    segment_ordinal: int


class SeedMeeting(FixtureModel):
    title: str
    occurred_at: str
    duration_ms: int
    tag: str
    participants: list[Person]
    segments: list[SeedSegment]
    chapters: list[SeedChapter]
    tasks: list[SeedTask]
    points: list[SeedPoint]
    overview: str
    sample_media_key: str | None = None


class SeedTemplate(FixtureModel):
    schema_version: int
    meetings: list[SeedMeeting]


def bootstrap(db: Session, session_id: str) -> tuple[str, str]:
    UUID(session_id)
    existing = (
        db.execute(select(demo_sessions).where(demo_sessions.c.id == session_id)).mappings().first()
    )
    if existing:
        return str(existing["workspace_id"]), str(existing["user_id"])
    workspace_id, user_id = uid(), uid()
    db.execute(insert(workspaces).values(id=workspace_id, name="Acme workspace"))
    db.execute(
        insert(users).values(
            id=user_id, display_name="Alex Morgan", email="alex.morgan@example.com"
        )
    )
    db.execute(insert(memberships).values(workspace_id=workspace_id, user_id=user_id, role="owner"))
    db.execute(
        insert(demo_sessions).values(
            id=session_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expires_at=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
            last_seen_at=now(),
        )
    )
    db.execute(insert(preferences).values(workspace_id=workspace_id, user_id=user_id))
    template_path = Path(__file__).resolve().parents[2] / "fixtures" / "seed-v1.json"
    template = SeedTemplate.model_validate_json(template_path.read_bytes())
    people: dict[str, str] = {}
    tag_ids: dict[str, str] = {}
    for fixture in template.meetings:
        meeting_id = uid()
        scope = {"workspace_id": workspace_id, "meeting_id": meeting_id}
        db.execute(
            insert(meetings).values(
                id=meeting_id,
                workspace_id=workspace_id,
                created_by_id=user_id,
                title=fixture.title,
                occurred_at=fixture.occurred_at,
                duration_ms=fixture.duration_ms,
                source="seeded",
                media_mode="sample" if fixture.sample_media_key else "simulated",
                sample_media_key=fixture.sample_media_key,
                description="Synthetic demonstration meeting",
            )
        )
        local_people: dict[str, str] = {}
        for person in fixture.participants:
            if person.email not in people:
                people[person.email] = uid()
                db.execute(
                    insert(participants).values(
                        id=people[person.email],
                        workspace_id=workspace_id,
                        display_name=person.display_name,
                        normalized_email=person.email,
                    )
                )
            person_id = people[person.email]
            local_people[person.display_name] = person_id
            db.execute(insert(attendees).values(**scope, participant_id=person_id, role="attendee"))
        speaker_ids: dict[str, str] = {}
        segment_ids: list[str] = []
        for ordinal, segment in enumerate(fixture.segments):
            if segment.speaker not in speaker_ids:
                speaker_ids[segment.speaker] = uid()
                position = len(speaker_ids) - 1
                db.execute(
                    insert(speakers).values(
                        **scope,
                        id=speaker_ids[segment.speaker],
                        participant_id=local_people.get(segment.speaker),
                        display_name=segment.speaker,
                        stable_color_key=position % 8,
                        position=position,
                    )
                )
            segment_id = uid()
            segment_ids.append(segment_id)
            db.execute(
                insert(segments).values(
                    **scope,
                    public_id=segment_id,
                    ordinal=ordinal,
                    speaker_id=speaker_ids[segment.speaker],
                    start_ms=segment.start_ms,
                    end_ms=segment.end_ms,
                    text=segment.text,
                )
            )
        summary_id = uid()
        db.execute(
            insert(summaries).values(
                **scope,
                id=summary_id,
                overview=fixture.overview,
                notes="",
                provider="extractive",
                source_revision=1,
                generated_at=now(),
            )
        )
        for position, point in enumerate(fixture.points):
            db.execute(
                insert(summary_points).values(
                    **scope,
                    summary_id=summary_id,
                    kind=point.kind,
                    text=point.text,
                    position=position,
                    source_segment_id=segment_ids[point.segment_ordinal],
                )
            )
        for chapter in fixture.chapters:
            db.execute(insert(chapters).values(**scope, **chapter.model_dump(), source_revision=1))
        for task in fixture.tasks:
            db.execute(
                insert(action_items).values(
                    **scope,
                    text=task.text,
                    status=task.status,
                    completed_at=now() if task.status == "completed" else None,
                    assignee_participant_id=local_people[task.owner],
                    source_revision=1,
                    source_segment_id=segment_ids[task.segment_ordinal],
                    origin="extracted",
                )
            )
        if fixture.tag not in tag_ids:
            tag_ids[fixture.tag] = uid()
            db.execute(
                insert(tags).values(
                    id=tag_ids[fixture.tag],
                    workspace_id=workspace_id,
                    name=fixture.tag,
                    normalized_name=fixture.tag.casefold(),
                    color="purple",
                )
            )
        db.execute(insert(meeting_tags).values(**scope, tag_id=tag_ids[fixture.tag]))
    db.execute(
        insert(activity_events).values(
            workspace_id=workspace_id,
            actor_id=user_id,
            kind="workspace.created",
            text="Your private demo workspace is ready",
        )
    )
    return workspace_id, user_id
