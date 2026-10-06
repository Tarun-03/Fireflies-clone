from sqlalchemy import Table, select
from sqlalchemy.engine import RowMapping

from app.api.dependencies import Scope
from app.core.errors import DomainError


def get_resource(
    scope: Scope, table: Table, resource_id: str, meeting_id: str | None = None
) -> RowMapping:
    query = select(table).where(
        table.c.workspace_id == scope.workspace_id, table.c.id == resource_id
    )
    if meeting_id is not None:
        query = query.where(table.c.meeting_id == meeting_id)
    row = scope.db.execute(query).mappings().first()
    if row is None:
        raise DomainError(404, "not_found", "This item could not be found.")
    return row
