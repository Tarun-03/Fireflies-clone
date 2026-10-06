from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select, update

from app.api.dependencies import Scoped, Version, require_version
from app.models import chapters, meetings, summaries, summary_points
from app.repositories.scoped import get_resource
from app.schemas.notebook import Chapter, NotesUpdate, Summary, SummaryPoint

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
