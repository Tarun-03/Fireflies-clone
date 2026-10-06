from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session

from app.api.dependencies import Scoped, Version, require_version, service_auth, session_header
from app.core.config import get_settings
from app.core.limits import check_storage, rate_limit
from app.db.engine import engine
from app.db.session import begin_write
from app.models import (
    activity_events,
    demo_sessions,
    participants,
    preferences,
    tags,
    users,
    workspaces,
)
from app.models.common import uid
from app.repositories.scoped import get_resource
from app.schemas.common import Page
from app.schemas.intelligence import IntelligenceStatus
from app.schemas.workspace import (
    Activity,
    ActivityUpdate,
    Participant,
    ParticipantUpdate,
    Preferences,
    PreferencesUpdate,
    Profile,
    SessionResult,
    Tag,
    TagInput,
)
from app.services.seed import bootstrap

router = APIRouter(prefix="/api/v1")


@router.post("/demo/session", response_model=SessionResult, dependencies=[Depends(service_auth)])
def session_create(session_id: Annotated[str, Depends(session_header)]) -> SessionResult:
    rate_limit("global", "bootstrap", 20)
    with Session(engine) as db:
        begin_write(db)
        if db.scalar(select(demo_sessions.c.id).where(demo_sessions.c.id == session_id)) is None:
            check_storage(db, added_bytes=200000)
        bootstrap(db, session_id)
        db.commit()
    return SessionResult()


@router.get("/me", response_model=Profile)
def profile(scope: Scoped) -> Profile:
    user = scope.db.execute(select(users).where(users.c.id == scope.user_id)).mappings().one()
    name = scope.db.scalar(select(workspaces.c.name).where(workspaces.c.id == scope.workspace_id))
    return Profile(
        id=user["id"],
        display_name=user["display_name"],
        workspace_name=str(name),
        preferences=read_preferences(scope),
        ai_available=get_settings().llm_provider == "openai",
    )


@router.get("/me/preferences", response_model=Preferences)
def read_preferences(scope: Scoped) -> Preferences:
    row = (
        scope.db.execute(
            select(preferences).where(
                preferences.c.workspace_id == scope.workspace_id,
                preferences.c.user_id == scope.user_id,
            )
        )
        .mappings()
        .one()
    )
    return Preferences.model_validate(row)


@router.patch("/me/preferences", response_model=Preferences)
def write_preferences(
    data: PreferencesUpdate, scope: Scoped, if_match: Version = None
) -> Preferences:
    current = read_preferences(scope)
    require_version(current.version, if_match)
    scope.db.execute(
        update(preferences)
        .where(
            preferences.c.workspace_id == scope.workspace_id, preferences.c.user_id == scope.user_id
        )
        .values(**data.model_dump(exclude_none=True), version=current.version + 1)
    )
    return read_preferences(scope)


@router.get("/participants", response_model=Page[Participant])
def list_participants(
    scope: Scoped, q: str = Query("", max_length=120), limit: int = Query(100, ge=1, le=100)
) -> Page[Participant]:
    rows = scope.db.execute(
        select(participants)
        .where(
            participants.c.workspace_id == scope.workspace_id,
            participants.c.display_name.icontains(q, autoescape=True),
        )
        .order_by(participants.c.display_name, participants.c.id)
        .limit(limit)
    ).mappings()
    return Page(items=[Participant.model_validate(row) for row in rows])


@router.patch("/participants/{participant_id}", response_model=Participant)
def edit_participant(
    participant_id: UUID, data: ParticipantUpdate, scope: Scoped, if_match: Version = None
) -> Participant:
    current = get_resource(scope, participants, str(participant_id))
    require_version(current["version"], if_match)
    scope.db.execute(
        update(participants)
        .where(participants.c.id == str(participant_id))
        .values(display_name=data.display_name, version=current["version"] + 1)
    )
    return Participant.model_validate(get_resource(scope, participants, str(participant_id)))


@router.get("/tags", response_model=Page[Tag])
def list_tags(scope: Scoped) -> Page[Tag]:
    rows = scope.db.execute(
        select(tags)
        .where(tags.c.workspace_id == scope.workspace_id)
        .order_by(tags.c.normalized_name)
        .limit(100)
    ).mappings()
    return Page(items=[Tag.model_validate(row) for row in rows])


@router.post("/tags", response_model=Tag, status_code=201)
def create_tag(data: TagInput, scope: Scoped) -> Tag:
    tag_id = uid()
    scope.db.execute(
        insert(tags).values(
            id=tag_id,
            workspace_id=scope.workspace_id,
            name=data.name,
            normalized_name=data.name.casefold(),
            color=data.color,
        )
    )
    return Tag.model_validate(get_resource(scope, tags, tag_id))


@router.patch("/tags/{tag_id}", response_model=Tag)
def edit_tag(tag_id: UUID, data: TagInput, scope: Scoped, if_match: Version = None) -> Tag:
    row = get_resource(scope, tags, str(tag_id))
    require_version(row["version"], if_match)
    scope.db.execute(
        update(tags)
        .where(tags.c.id == str(tag_id))
        .values(
            name=data.name,
            normalized_name=data.name.casefold(),
            color=data.color,
            version=row["version"] + 1,
        )
    )
    return Tag.model_validate(get_resource(scope, tags, str(tag_id)))


@router.delete("/tags/{tag_id}", status_code=204)
def delete_tag(tag_id: UUID, scope: Scoped, if_match: Version = None) -> None:
    row = get_resource(scope, tags, str(tag_id))
    require_version(row["version"], if_match)
    scope.db.execute(delete(tags).where(tags.c.id == str(tag_id)))


@router.get("/activity", response_model=Page[Activity])
def activity(scope: Scoped, limit: int = Query(50, ge=1, le=100)) -> Page[Activity]:
    rows = scope.db.execute(
        select(activity_events)
        .where(activity_events.c.workspace_id == scope.workspace_id)
        .order_by(activity_events.c.created_at.desc(), activity_events.c.id.desc())
        .limit(limit)
    ).mappings()
    return Page(items=[Activity.model_validate(row) for row in rows])


@router.patch("/activity/{event_id}", response_model=Activity)
def mark_activity(
    event_id: UUID, data: ActivityUpdate, scope: Scoped, if_match: Version = None
) -> Activity:
    row = get_resource(scope, activity_events, str(event_id))
    require_version(row["version"], if_match)
    scope.db.execute(
        update(activity_events)
        .where(activity_events.c.id == str(event_id))
        .values(is_read=data.is_read, version=row["version"] + 1)
    )
    return Activity.model_validate(get_resource(scope, activity_events, str(event_id)))


@router.get("/intelligence", response_model=IntelligenceStatus)
def intelligence_status(scope: Scoped) -> IntelligenceStatus:
    settings = get_settings()
    return IntelligenceStatus(
        available=settings.llm_provider == "openai",
        provider=settings.llm_provider,
        model=settings.llm_model or None,
        context_characters=24000,
    )
