from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Table,
    UniqueConstraint,
)

from app.models.common import identity, metadata, timestamps, version

workspaces = Table(
    "workspaces", metadata, identity(), Column("name", String(200), nullable=False), *timestamps()
)
users = Table(
    "users",
    metadata,
    identity(),
    Column("display_name", String(120), nullable=False),
    Column("email", String(254)),
    *timestamps(),
)
memberships = Table(
    "workspace_memberships",
    metadata,
    Column("workspace_id", ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String, nullable=False, default="owner"),
    CheckConstraint("role IN ('owner')", name="role"),
)
demo_sessions = Table(
    "demo_sessions",
    metadata,
    identity(),
    Column("workspace_id", String(36), nullable=False, unique=True),
    Column("user_id", String(36), nullable=False),
    Column("expires_at", String, nullable=False),
    Column("last_seen_at", String, nullable=False),
    *timestamps(),
    ForeignKeyConstraint(
        ["workspace_id", "user_id"],
        ["workspace_memberships.workspace_id", "workspace_memberships.user_id"],
        ondelete="CASCADE",
    ),
)
preferences = Table(
    "user_preferences",
    metadata,
    Column("workspace_id", String(36), primary_key=True),
    Column("user_id", String(36), primary_key=True),
    Column("theme", String, nullable=False, default="system"),
    Column("timezone", String(80), nullable=False, default="Asia/Kolkata"),
    Column("player_speed", Float, nullable=False, default=1.0),
    Column("reduced_motion", Boolean, nullable=False, default=False),
    version(),
    *timestamps(),
    CheckConstraint("theme IN ('light','dark','system')", name="theme"),
    CheckConstraint("player_speed IN (0.5,0.75,1,1.25,1.5,2)", name="speed"),
    ForeignKeyConstraint(
        ["workspace_id", "user_id"],
        ["workspace_memberships.workspace_id", "workspace_memberships.user_id"],
        ondelete="CASCADE",
    ),
)
participants = Table(
    "participants",
    metadata,
    identity(),
    Column("workspace_id", ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("display_name", String(120), nullable=False),
    Column("normalized_email", String(254)),
    version(),
    *timestamps(),
    UniqueConstraint("workspace_id", "id"),
    UniqueConstraint("workspace_id", "normalized_email"),
)
