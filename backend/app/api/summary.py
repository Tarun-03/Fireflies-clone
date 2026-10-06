import hashlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request
from sqlalchemy import delete, insert, select, update

from app.api.dependencies import Scoped, Version, require_version
from app.api.transcript import transcript_page
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.limits import rate_limit
from app.db.session import begin_write
from app.models import action_items, chapters, meetings, summaries, summary_points
from app.models.common import now
from app.repositories.scoped import get_resource
from app.schemas.intelligence import RegenerateRequest
from app.schemas.notebook import Chapter, NotesUpdate, Summary, SummaryPoint
from app.services.activity import record_activity
from app.services.intelligence import generate_summary, while_connected
from app.services.operations import claim, complete, fail

router = APIRouter(prefix="/api/v1/meetings")


@router.get("/{meeting_id}/summary", response_model=Summary)
def summary(meeting_id: UUID, scope: Scoped) -> Summary:
    meeting = get_resource(scope, meetings, str(meeting_id))
    row = (
        scope.db.execute(
            select(summaries).where(
                summaries.c.workspace_id == scope.workspace_id,
                summaries.c.meeting_id == str(meeting_id),
            )
        )
        .mappings()
        .one()
    )
    points = [
        SummaryPoint.model_validate(point)
        for point in scope.db.execute(
            select(summary_points)
            .where(
                summary_points.c.workspace_id == scope.workspace_id,
                summary_points.c.meeting_id == str(meeting_id),
            )
            .order_by(summary_points.c.position)
            .limit(100)
        ).mappings()
    ]
    return Summary.model_validate(
        dict(row)
        | {"points": points, "stale": row["source_revision"] != meeting["transcript_revision"]}
    )


@router.patch("/{meeting_id}/summary", response_model=Summary)
def notes(meeting_id: UUID, data: NotesUpdate, scope: Scoped, if_match: Version = None) -> Summary:
    current = summary(meeting_id, scope)
    require_version(current.version, if_match)
    scope.db.execute(
        update(summaries)
        .where(summaries.c.id == str(current.id))
        .values(notes=data.notes, version=current.version + 1)
    )
    return summary(meeting_id, scope)


@router.get("/{meeting_id}/chapters", response_model=list[Chapter])
def outline(meeting_id: UUID, scope: Scoped) -> list[Chapter]:
    get_resource(scope, meetings, str(meeting_id))
    return [
        Chapter.model_validate(row)
        for row in scope.db.execute(
            select(chapters)
            .where(
                chapters.c.workspace_id == scope.workspace_id,
                chapters.c.meeting_id == str(meeting_id),
            )
            .order_by(chapters.c.position)
            .limit(100)
        ).mappings()
    ]


@router.post("/{meeting_id}/summary/regenerate", response_model=Summary)
async def regenerate(
    meeting_id: UUID,
    data: RegenerateRequest,
    request: Request,
    scope: Scoped,
    idempotency_key: Annotated[UUID, Header()],
    if_match: Version = None,
) -> Summary:
    meeting = get_resource(scope, meetings, str(meeting_id))
    current = summary(meeting_id, scope)
    rate_limit(scope.session_id, "generation", 5)
    endpoint = f"summary:{meeting_id}"
    key = str(idempotency_key)
    digest = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
    replay = claim(scope, endpoint, key, digest)
    if replay:
        return Summary.model_validate_json(replay)
    require_version(current.version, if_match)
    if data.mode == "openai" and not data.consent:
        raise DomainError(
            422,
            "consent_required",
            "Confirm sending selected transcript text to OpenAI, or choose extractive mode.",
        )
    rows = []
    offset = 0
    while True:
        page = transcript_page(scope, str(meeting_id), offset, 100)
        rows.extend(page.items)
        if page.next_cursor is None:
            break
        offset = page.next_cursor
    revision = meeting["transcript_revision"]
    scope.db.commit()  # Release the writer before any provider work.
    try:
        generated, provider, notice = await while_connected(
            request, generate_summary(rows, str(meeting_id), revision, data.mode)
        )
        begin_write(scope.db)
        latest = get_resource(scope, meetings, str(meeting_id))
        if latest["transcript_revision"] != revision:
            raise DomainError(
                409,
                "transcript_changed",
                "The transcript changed during generation. Regenerate from its latest revision.",
            )
        latest_summary = summary(meeting_id, scope)
        require_version(latest_summary.version, str(current.version))
        scope.db.execute(
            update(summaries)
            .where(summaries.c.id == str(current.id))
            .values(
                overview=generated.overview,
                provider=provider,
                model=get_settings().llm_model if provider == "openai" else None,
                source_revision=revision,
                generated_at=now(),
                version=current.version + 1,
            )
        )
        scope.db.execute(
            delete(summary_points).where(
                summary_points.c.meeting_id == str(meeting_id),
                summary_points.c.workspace_id == scope.workspace_id,
            )
        )
        context = {"workspace_id": scope.workspace_id, "meeting_id": str(meeting_id)}
        for kind, items in [("key_point", generated.key_points), ("decision", generated.decisions)]:
            for position, item in enumerate(items):
                scope.db.execute(
                    insert(summary_points).values(
                        **context,
                        summary_id=str(current.id),
                        kind=kind,
                        text=item.text,
                        position=position,
                        source_segment_id=item.segment_id,
                    )
                )
        # Only untouched, open extracted tasks are replaced. Personal work always survives.
        scope.db.execute(
            delete(action_items).where(
                action_items.c.meeting_id == str(meeting_id),
                action_items.c.workspace_id == scope.workspace_id,
                action_items.c.origin == "extracted",
                action_items.c.status == "open",
                action_items.c.user_edited.is_(False),
            )
        )
        existing = {
            text.casefold().strip()
            for text in scope.db.scalars(
                select(action_items.c.text).where(
                    action_items.c.meeting_id == str(meeting_id),
                    action_items.c.workspace_id == scope.workspace_id,
                )
            )
        }
        for task in generated.tasks:
            if task.text.casefold().strip() not in existing:
                if len(existing) >= 100:
                    raise DomainError(
                        429,
                        "task_quota",
                        "Remove tasks before regenerating this meeting; its 100-task limit"
                        " would be exceeded.",
                    )
                existing.add(task.text.casefold().strip())
                scope.db.execute(
                    insert(action_items).values(
                        **context,
                        text=task.text,
                        origin="extracted",
                        source_segment_id=task.segment_id,
                        source_revision=revision,
                    )
                )
        scope.db.execute(
            delete(chapters).where(
                chapters.c.meeting_id == str(meeting_id),
                chapters.c.workspace_id == scope.workspace_id,
            )
        )
        chunk = max(1, (len(rows) + 5) // 6)
        for position, start in enumerate(range(0, len(rows), chunk)):
            group = rows[start : start + chunk]
            scope.db.execute(
                insert(chapters).values(
                    **context,
                    title=group[0].text[:80],
                    description=group[0].text[:500],
                    start_ms=min(r.start_ms for r in group),
                    end_ms=max(r.end_ms for r in group),
                    position=position,
                    source_revision=revision,
                )
            )
        record_activity(
            scope, "summary.regenerated", "Meeting notes were regenerated", str(meeting_id)
        )
        result = summary(meeting_id, scope).model_copy(update={"notice": notice})
        complete(scope, endpoint, key, result.model_dump_json())
        return result
    except BaseException:
        fail(scope, endpoint, key)
        raise
