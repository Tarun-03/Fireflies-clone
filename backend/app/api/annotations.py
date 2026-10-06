from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import Table, delete, func, insert, select, update
from starlette.responses import Response

from app.api.dependencies import Scoped, Version, require_version
from app.api.segments import scoped_segment
from app.core.errors import DomainError
from app.models import comments, highlights, meetings, segments, soundbites, speakers
from app.models.common import uid
from app.repositories.scoped import get_resource
from app.schemas.annotations import (
    Comment,
    CommentCreate,
    CommentUpdate,
    Highlight,
    HighlightCreate,
    HighlightUpdate,
    Soundbite,
    SoundbiteInput,
)
from app.schemas.common import Page

router = APIRouter(prefix="/api/v1/meetings")


def listed[T: BaseModel](
    scope: Scoped, meeting_id: UUID, table: Table, model: type[T], cursor: UUID | None
) -> Page[T]:
    get_resource(scope, meetings, str(meeting_id))
    query = select(table).where(
        table.c.workspace_id == scope.workspace_id, table.c.meeting_id == str(meeting_id)
    )
    if cursor:
        query = query.where(table.c.id > str(cursor))
    rows = scope.db.execute(query.order_by(table.c.id).limit(51)).mappings().all()
    result: list[T] = []
    used = 0
    for row in rows[:50]:
        item = model.model_validate(row)
        size = len(item.model_dump_json().encode())
        if used + size > 512 * 1024 and result:
            break
        result.append(item)
        used += size
    more = len(rows) > len(result)
    return Page(
        items=result, has_more=more, next_cursor=str(rows[len(result) - 1]["id"]) if more else None
    )


def room(scope: Scoped, meeting_id: UUID, table: Table, maximum: int = 500) -> None:
    get_resource(scope, meetings, str(meeting_id))
    count = (
        scope.db.scalar(
            select(func.count())
            .select_from(table)
            .where(
                table.c.workspace_id == scope.workspace_id, table.c.meeting_id == str(meeting_id)
            )
        )
        or 0
    )
    if count >= maximum:
        raise DomainError(
            429,
            "annotation_quota",
            f"This meeting has reached its {maximum}-item limit for these annotations.",
        )


def owner(
    scope: Scoped, table: Table, meeting_id: UUID, item_id: UUID, version: str | None
) -> None:
    row = get_resource(scope, table, str(item_id), str(meeting_id))
    if row["author_id"] != scope.user_id:
        raise DomainError(403, "author_required", "Only the author can edit this annotation.")
    require_version(row["version"], version)


@router.get("/{meeting_id}/comments", response_model=Page[Comment])
def list_comments(meeting_id: UUID, scope: Scoped, cursor: UUID | None = None) -> Page[Comment]:
    return listed(scope, meeting_id, comments, Comment, cursor)


@router.post("/{meeting_id}/comments", response_model=Comment, status_code=201)
def add_comment(meeting_id: UUID, data: CommentCreate, scope: Scoped) -> Comment:
    segment = scoped_segment(scope, meeting_id, data.segment_id)
    require_version(segment.version, str(data.segment_version))
    room(scope, meeting_id, comments)
    item_id = uid()
    scope.db.execute(
        insert(comments).values(
            id=item_id,
            workspace_id=scope.workspace_id,
            meeting_id=str(meeting_id),
            author_id=scope.user_id,
            segment_id=str(data.segment_id),
            body=data.body,
        )
    )
    return Comment.model_validate(get_resource(scope, comments, item_id, str(meeting_id)))


@router.patch("/{meeting_id}/comments/{item_id}", response_model=Comment)
def edit_comment(
    meeting_id: UUID, item_id: UUID, data: CommentUpdate, scope: Scoped, if_match: Version = None
) -> Comment:
    owner(scope, comments, meeting_id, item_id, if_match)
    scope.db.execute(
        update(comments)
        .where(comments.c.id == str(item_id))
        .values(body=data.body, version=comments.c.version + 1)
    )
    return Comment.model_validate(get_resource(scope, comments, str(item_id), str(meeting_id)))


@router.delete("/{meeting_id}/comments/{item_id}", status_code=204)
def delete_comment(
    meeting_id: UUID, item_id: UUID, scope: Scoped, if_match: Version = None
) -> None:
    owner(scope, comments, meeting_id, item_id, if_match)
    scope.db.execute(delete(comments).where(comments.c.id == str(item_id)))


@router.get("/{meeting_id}/highlights", response_model=Page[Highlight])
def list_highlights(meeting_id: UUID, scope: Scoped, cursor: UUID | None = None) -> Page[Highlight]:
    return listed(scope, meeting_id, highlights, Highlight, cursor)


@router.post("/{meeting_id}/highlights", response_model=Highlight, status_code=201)
def add_highlight(meeting_id: UUID, data: HighlightCreate, scope: Scoped) -> Highlight:
    segment = scoped_segment(scope, meeting_id, data.segment_id)
    require_version(segment.version, str(data.segment_version))
    if (
        data.end_offset <= data.start_offset
        or data.end_offset > len(segment.text)
        or segment.text[data.start_offset : data.end_offset] != data.selected_text
    ):
        raise DomainError(
            422, "invalid_selection", "The selected text does not match this transcript version."
        )
    room(scope, meeting_id, highlights)
    item_id = uid()
    scope.db.execute(
        insert(highlights).values(
            id=item_id,
            workspace_id=scope.workspace_id,
            meeting_id=str(meeting_id),
            author_id=scope.user_id,
            **data.model_dump(mode="json", exclude={"segment_version"}),
        )
    )
    return Highlight.model_validate(get_resource(scope, highlights, item_id, str(meeting_id)))


@router.patch("/{meeting_id}/highlights/{item_id}", response_model=Highlight)
def edit_highlight(
    meeting_id: UUID, item_id: UUID, data: HighlightUpdate, scope: Scoped, if_match: Version = None
) -> Highlight:
    owner(scope, highlights, meeting_id, item_id, if_match)
    scope.db.execute(
        update(highlights)
        .where(highlights.c.id == str(item_id))
        .values(**data.model_dump(), version=highlights.c.version + 1)
    )
    return Highlight.model_validate(get_resource(scope, highlights, str(item_id), str(meeting_id)))


@router.delete("/{meeting_id}/highlights/{item_id}", status_code=204)
def delete_highlight(
    meeting_id: UUID, item_id: UUID, scope: Scoped, if_match: Version = None
) -> None:
    owner(scope, highlights, meeting_id, item_id, if_match)
    scope.db.execute(delete(highlights).where(highlights.c.id == str(item_id)))


@router.get("/{meeting_id}/soundbites", response_model=Page[Soundbite])
def list_soundbites(meeting_id: UUID, scope: Scoped, cursor: UUID | None = None) -> Page[Soundbite]:
    return listed(scope, meeting_id, soundbites, Soundbite, cursor)


def soundbite_bounds(scope: Scoped, meeting_id: UUID, data: SoundbiteInput) -> None:
    meeting = get_resource(scope, meetings, str(meeting_id))
    if data.end_ms > meeting["duration_ms"]:
        raise DomainError(422, "invalid_time", "The interval must fit within the meeting duration.")


@router.post("/{meeting_id}/soundbites", response_model=Soundbite, status_code=201)
def add_soundbite(meeting_id: UUID, data: SoundbiteInput, scope: Scoped) -> Soundbite:
    soundbite_bounds(scope, meeting_id, data)
    room(scope, meeting_id, soundbites, 100)
    item_id = uid()
    scope.db.execute(
        insert(soundbites).values(
            id=item_id,
            workspace_id=scope.workspace_id,
            meeting_id=str(meeting_id),
            author_id=scope.user_id,
            **data.model_dump(),
        )
    )
    return Soundbite.model_validate(get_resource(scope, soundbites, item_id, str(meeting_id)))


@router.patch("/{meeting_id}/soundbites/{item_id}", response_model=Soundbite)
def edit_soundbite(
    meeting_id: UUID, item_id: UUID, data: SoundbiteInput, scope: Scoped, if_match: Version = None
) -> Soundbite:
    owner(scope, soundbites, meeting_id, item_id, if_match)
    soundbite_bounds(scope, meeting_id, data)
    scope.db.execute(
        update(soundbites)
        .where(soundbites.c.id == str(item_id))
        .values(**data.model_dump(), version=soundbites.c.version + 1)
    )
    return Soundbite.model_validate(get_resource(scope, soundbites, str(item_id), str(meeting_id)))


@router.delete("/{meeting_id}/soundbites/{item_id}", status_code=204)
def delete_soundbite(
    meeting_id: UUID, item_id: UUID, scope: Scoped, if_match: Version = None
) -> None:
    owner(scope, soundbites, meeting_id, item_id, if_match)
    scope.db.execute(delete(soundbites).where(soundbites.c.id == str(item_id)))


def stamp(ms: int) -> str:
    total = ms // 1000
    return f"{total // 3600:02}:{total // 60 % 60:02}:{total % 60:02}"


@router.get("/{meeting_id}/soundbites/{item_id}/export")
def excerpt(
    meeting_id: UUID, item_id: UUID, scope: Scoped, format: str = Query("txt", pattern="^txt$")
) -> Response:
    item = get_resource(scope, soundbites, str(item_id), str(meeting_id))
    rows = scope.db.execute(
        select(segments.c.start_ms, segments.c.text, speakers.c.display_name)
        .join(speakers, speakers.c.id == segments.c.speaker_id)
        .where(
            segments.c.workspace_id == scope.workspace_id,
            segments.c.meeting_id == str(meeting_id),
            segments.c.start_ms < item["end_ms"],
            segments.c.end_ms > item["start_ms"],
        )
        .order_by(segments.c.start_ms, segments.c.ordinal)
        .limit(3000)
    ).mappings()
    content = (
        f"{item['title']}\n{stamp(item['start_ms'])}–{stamp(item['end_ms'])}\n"
        "Timestamped text excerpt; no audio clipping. Full overlapping turns are included.\n\n"
        + "\n\n".join(
            f"[{stamp(row['start_ms'])}] {row['display_name']}: {row['text']}" for row in rows
        )
    )
    return Response(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="soundbite.txt"'},
    )
