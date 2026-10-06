from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, ForeignKeyConstraint, Integer, MetaData, String

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def uid() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def identity() -> Column[str]:
    return Column("id", String(36), primary_key=True, default=uid)


def version() -> Column[int]:
    return Column("version", Integer, nullable=False, default=1, server_default="1")


def timestamps() -> tuple[Column[str], Column[str]]:
    return (
        Column("created_at", String, nullable=False, default=now),
        Column("updated_at", String, nullable=False, default=now, onupdate=now),
    )


def meeting_fk() -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["workspace_id", "meeting_id"], ["meetings.workspace_id", "meetings.id"], ondelete="CASCADE"
    )


def segment_fk(column: str = "segment_id") -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["workspace_id", "meeting_id", column],
        [
            "transcript_segments.workspace_id",
            "transcript_segments.meeting_id",
            "transcript_segments.public_id",
        ],
    )


def author_fk() -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["workspace_id", "author_id"],
        ["workspace_memberships.workspace_id", "workspace_memberships.user_id"],
    )
