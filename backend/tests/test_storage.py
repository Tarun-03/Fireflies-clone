from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.db.engine import make_engine
from app.models import (
    action_items,
    attendees,
    chapters,
    chat_citations,
    chat_messages,
    comments,
    highlights,
    meetings,
    search_documents,
    segments,
    soundbites,
    speakers,
)
from app.models.common import uid
from app.services.seed import bootstrap
from scripts.storage import backup


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    database_path = tmp_path / "workspace.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    engine = make_engine(f"sqlite:///{database_path}")
    with Session(engine) as db:
        yield db
    engine.dispose()
    get_settings.cache_clear()


def seed(db: Session) -> tuple[str, str]:
    result = bootstrap(db, str(uuid4()))
    db.commit()
    return result


def test_atomic_idempotent_seed_and_foreign_keys(database: Session) -> None:
    session_id = str(uuid4())
    workspace, user = bootstrap(database, session_id)
    database.commit()
    assert bootstrap(database, session_id) == (workspace, user)
    assert database.scalar(select(func.count()).select_from(meetings)) == 8
    assert database.scalar(select(func.count()).select_from(segments)) == 320
    assert database.scalar(select(func.count()).select_from(search_documents)) == 328
    assert database.execute(text("PRAGMA foreign_key_check")).all() == []
    assert database.scalar(text("PRAGMA foreign_keys")) == 1
    assert database.scalar(text("PRAGMA journal_mode")) == "wal"
    meeting_id = database.scalar(select(meetings.c.id))
    database.execute(delete(meetings).where(meetings.c.id == meeting_id))
    database.commit()
    bootstrap(database, session_id)
    assert database.scalar(select(func.count()).select_from(meetings)) == 7


def test_separate_workspaces_and_rollback(database: Session) -> None:
    one, _ = seed(database)
    two, _ = bootstrap(database, str(uuid4()))
    assert one != two
    assert database.scalar(select(func.count()).select_from(meetings)) == 16
    database.rollback()
    assert database.scalar(select(func.count()).select_from(meetings)) == 8
    assert database.scalar(select(func.count()).select_from(search_documents)) == 328


def test_cross_meeting_speaker_rejected(database: Session) -> None:
    seed(database)
    rows = database.execute(select(segments).limit(1)).mappings().all()
    segment = rows[0]
    foreign = database.scalar(
        select(speakers.c.id).where(speakers.c.meeting_id != segment["meeting_id"])
    )
    with pytest.raises(IntegrityError):
        database.execute(
            update(segments)
            .where(segments.c.public_id == segment["public_id"])
            .values(speaker_id=foreign)
        )
    database.rollback()


def test_cross_workspace_attendee_rejected(database: Session) -> None:
    one, _ = seed(database)
    two, _ = seed(database)
    meeting_id = database.scalar(select(meetings.c.id).where(meetings.c.workspace_id == one))
    foreign = database.scalar(
        select(attendees.c.participant_id).where(attendees.c.workspace_id == two)
    )
    with pytest.raises(IntegrityError):
        database.execute(
            insert(attendees).values(
                workspace_id=one, meeting_id=meeting_id, participant_id=foreign
            )
        )
    database.rollback()


@pytest.mark.parametrize("table", [segments, chapters, soundbites])
def test_interval_checks(database: Session, table: object) -> None:
    from sqlalchemy import Table

    assert isinstance(table, Table)
    workspace, user = seed(database)
    meeting = database.execute(select(meetings)).mappings().first()
    assert meeting is not None
    with pytest.raises(IntegrityError):
        if table is soundbites:
            database.execute(
                insert(soundbites).values(
                    workspace_id=workspace,
                    meeting_id=meeting["id"],
                    author_id=user,
                    title="Invalid",
                    start_ms=0,
                    end_ms=meeting["duration_ms"] + 1,
                )
            )
        else:
            database.execute(
                update(table)
                .where(table.c.meeting_id == meeting["id"])
                .values(end_ms=meeting["duration_ms"] + 1)
            )
    database.rollback()


def test_unicode_highlight_and_explicit_invalidation(database: Session) -> None:
    workspace, user = seed(database)
    segment = database.execute(select(segments)).mappings().first()
    assert segment is not None
    database.execute(
        update(segments).where(segments.c.id == segment["id"]).values(text="Hello 🌍 café")
    )
    database.execute(
        insert(highlights).values(
            workspace_id=workspace,
            meeting_id=segment["meeting_id"],
            segment_id=segment["public_id"],
            author_id=user,
            start_offset=6,
            end_offset=7,
            selected_text="🌍",
        )
    )
    database.commit()
    with pytest.raises(IntegrityError):
        database.execute(
            update(segments).where(segments.c.id == segment["id"]).values(text="Changed")
        )
    database.rollback()


def test_segment_deletion_preserves_chat_snapshot(database: Session) -> None:
    workspace, user = seed(database)
    segment = database.execute(select(segments)).mappings().first()
    assert segment is not None
    scope = dict(workspace_id=workspace, meeting_id=segment["meeting_id"])
    message_id = uid()
    database.execute(
        insert(chat_messages).values(
            **scope,
            id=message_id,
            conversation_id=uid(),
            role="assistant",
            content="Synthetic excerpt",
            provider="extractive",
            source_revision=1,
        )
    )
    database.execute(
        insert(chat_citations).values(
            **scope,
            message_id=message_id,
            segment_id=segment["public_id"],
            original_segment_public_id=segment["public_id"],
            source_revision=1,
            timestamp_ms=segment["start_ms"],
        )
    )
    database.execute(
        insert(comments).values(
            **scope, segment_id=segment["public_id"], author_id=user, body="Test comment"
        )
    )
    database.execute(delete(segments).where(segments.c.id == segment["id"]))
    database.commit()
    assert database.scalar(select(func.count()).select_from(chat_messages)) == 1
    citation = database.execute(select(chat_citations)).mappings().one()
    assert citation["segment_id"] is None
    assert citation["original_segment_public_id"] == segment["public_id"]
    assert database.scalar(select(func.count()).select_from(comments)) == 0


def test_search_edit_rollback_rebuild_delete(database: Session) -> None:
    seed(database)
    segment = database.execute(select(segments)).mappings().first()
    assert segment is not None
    search = text(
        "SELECT count(*) FROM search_documents_fts WHERE search_documents_fts MATCH :query"
    )
    database.execute(
        update(segments).where(segments.c.id == segment["id"]).values(text="uniquekeyword")
    )
    assert database.scalar(search, {"query": '"uniquekeyword"'}) == 1
    database.rollback()
    assert database.scalar(search, {"query": '"uniquekeyword"'}) == 0
    database.execute(
        text("INSERT INTO search_documents_fts(search_documents_fts) VALUES('rebuild')")
    )
    database.execute(delete(meetings).where(meetings.c.id == segment["meeting_id"]))
    database.commit()
    assert database.scalar(select(func.count()).select_from(search_documents)) == 287
    assert database.execute(text("PRAGMA foreign_key_check")).all() == []


def test_backup_and_restore(database: Session, tmp_path: Path) -> None:
    import sqlite3

    seed(database)
    backup(tmp_path / "workspace.db", tmp_path / "backup.db")
    backup(tmp_path / "backup.db", tmp_path / "restored.db")
    with sqlite3.connect(tmp_path / "restored.db") as restored:
        assert restored.execute("SELECT count(*) FROM meetings").fetchone() == (8,)
        assert restored.execute("SELECT count(*) FROM action_items").fetchone() == (40,)


def test_task_status_and_duration(database: Session) -> None:
    seed(database)
    with pytest.raises(IntegrityError):
        database.execute(update(action_items).values(status="completed", completed_at=None))
    database.rollback()
    with pytest.raises(IntegrityError):
        database.execute(update(meetings).values(duration_ms=1000))
    database.rollback()
