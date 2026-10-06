from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import delete, insert, select, update

from app.api.dependencies import Scoped, Version, require_version
from app.core.errors import DomainError
from app.models import action_items, attendees, meetings
from app.models.common import now, uid
from app.repositories.scoped import get_resource
from app.schemas.common import Page
from app.schemas.meetings import Task, TaskInput, TaskUpdate
from app.services.activity import record_activity

router = APIRouter(prefix="/api/v1")


def validate_assignee(scope: Scoped, meeting_id: str, assignee: UUID | None) -> None:
    if (
        assignee is not None
        and scope.db.scalar(
            select(attendees.c.participant_id).where(
                attendees.c.workspace_id == scope.workspace_id,
                attendees.c.meeting_id == meeting_id,
                attendees.c.participant_id == str(assignee),
            )
        )
        is None
    ):
        raise DomainError(404, "not_found", "Choose an attendee from this meeting.")


@router.get("/action-items", response_model=Page[Task])
def workspace_tasks(
    scope: Scoped,
    status: Literal["open", "completed"] | None = None,
    limit: int = Query(100, ge=1, le=100),
    cursor: UUID | None = None,
) -> Page[Task]:
    query = select(action_items).where(action_items.c.workspace_id == scope.workspace_id)
    if status:
        query = query.where(action_items.c.status == status)
    if cursor:
        query = query.where(action_items.c.id > str(cursor))
    rows = scope.db.execute(query.order_by(action_items.c.id).limit(limit + 1)).mappings().all()
    more = len(rows) > limit
    return Page(
        items=[Task.model_validate(row) for row in rows[:limit]],
        has_more=more,
        next_cursor=rows[limit - 1]["id"] if more else None,
    )


@router.get("/meetings/{meeting_id}/action-items", response_model=Page[Task])
def meeting_tasks(meeting_id: UUID, scope: Scoped) -> Page[Task]:
    get_resource(scope, meetings, str(meeting_id))
    rows = scope.db.execute(
        select(action_items)
        .where(
            action_items.c.workspace_id == scope.workspace_id,
            action_items.c.meeting_id == str(meeting_id),
        )
        .order_by(action_items.c.created_at, action_items.c.id)
        .limit(100)
    ).mappings()
    return Page(items=[Task.model_validate(row) for row in rows])


@router.post("/meetings/{meeting_id}/action-items", response_model=Task, status_code=201)
def add_task(meeting_id: UUID, data: TaskInput, scope: Scoped) -> Task:
    get_resource(scope, meetings, str(meeting_id))
    validate_assignee(scope, str(meeting_id), data.assignee_participant_id)
    task_id = uid()
    scope.db.execute(
        insert(action_items).values(
            id=task_id,
            workspace_id=scope.workspace_id,
            meeting_id=str(meeting_id),
            **data.model_dump(mode="json"),
        )
    )
    record_activity(scope, "task.created", "An action item was added", str(meeting_id))
    return Task.model_validate(get_resource(scope, action_items, task_id, str(meeting_id)))


@router.patch("/meetings/{meeting_id}/action-items/{item_id}", response_model=Task)
def edit_task(
    meeting_id: UUID, item_id: UUID, data: TaskUpdate, scope: Scoped, if_match: Version = None
) -> Task:
    row = get_resource(scope, action_items, str(item_id), str(meeting_id))
    require_version(row["version"], if_match)
    validate_assignee(scope, str(meeting_id), data.assignee_participant_id)
    values = data.model_dump(mode="json", exclude_unset=True)
    if "status" in values:
        values["completed_at"] = now() if data.status == "completed" else None
    scope.db.execute(
        update(action_items)
        .where(action_items.c.id == str(item_id))
        .values(**values, version=row["version"] + 1, user_edited=True)
    )
    record_activity(scope, "task.updated", "An action item was updated", str(meeting_id))
    return Task.model_validate(get_resource(scope, action_items, str(item_id), str(meeting_id)))


@router.delete("/meetings/{meeting_id}/action-items/{item_id}", status_code=204)
def remove_task(meeting_id: UUID, item_id: UUID, scope: Scoped, if_match: Version = None) -> None:
    row = get_resource(scope, action_items, str(item_id), str(meeting_id))
    require_version(row["version"], if_match)
    scope.db.execute(delete(action_items).where(action_items.c.id == str(item_id)))
