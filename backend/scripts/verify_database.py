"""Verify the configured database with real application writes, then roll them back.

Run migrations first. This requires a read/write token. It neither provisions a
service nor proves hosted restart persistence; use persistence_probe for that.
"""

import argparse
from uuid import uuid4

from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import Scope
from app.core.config import get_settings
from app.db.engine import configured_engine
from app.db.session import begin_write
from app.models import action_items, comments, segments, workspaces
from app.services.search import find
from app.services.seed import bootstrap


def verify(db: Session) -> str:
    begin_write(db)
    session_id = str(uuid4())
    workspace, user = bootstrap(db, session_id)
    segment = (
        db.execute(select(segments).where(segments.c.workspace_id == workspace)).mappings().first()
    )
    assert segment is not None
    scope = Scope(db, workspace, user, session_id)
    marker = "compatibility" + uuid4().hex
    db.execute(update(segments).where(segments.c.id == segment["id"]).values(text=marker))
    assert str(find(scope, marker)[0].segment_id) == segment["public_id"]
    with db.begin_nested() as savepoint:
        db.execute(
            update(segments).where(segments.c.id == segment["id"]).values(text="rollbackprobe")
        )
        assert not find(scope, marker)
        savepoint.rollback()
    assert find(scope, marker)
    db.execute(
        insert(comments).values(
            workspace_id=workspace,
            meeting_id=segment["meeting_id"],
            segment_id=segment["public_id"],
            author_id=user,
            body="Compatibility probe",
        )
    )
    db.execute(
        insert(action_items).values(
            workspace_id=workspace,
            meeting_id=segment["meeting_id"],
            text="Compatibility task",
        )
    )
    try:
        with db.begin_nested():
            db.execute(
                update(segments)
                .where(segments.c.id == segment["id"])
                .values(speaker_id=str(uuid4()))
            )
    except IntegrityError:
        pass
    else:
        raise RuntimeError("Foreign key enforcement failed")
    assert db.scalar(text("PRAGMA foreign_keys")) == 1
    assert not db.execute(text("PRAGMA foreign_key_check")).all()
    db.rollback()
    return workspace


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-remote", action="store_true")
    args = parser.parse_args()
    if args.require_remote and not get_settings().remote_database:
        parser.error("Configure TURSO_DATABASE_URL and TURSO_AUTH_TOKEN for remote verification")
    engine = configured_engine()
    try:
        with Session(engine) as db:
            workspace = verify(db)
        engine.dispose()
        with Session(engine) as db:
            assert db.scalar(select(workspaces.c.id).where(workspaces.c.id == workspace)) is None
    finally:
        engine.dispose()
    mode = "remote Turso" if get_settings().remote_database else "local SQLite"
    print(f"PASS ({mode}): schema, foreign keys, savepoints, rollback, FTS triggers and search.")
    print("Probe writes rolled back. Hosted restart/redeploy still requires persistence_probe.")


if __name__ == "__main__":
    main()
