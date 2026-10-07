"""Reopen a real engine in a fresh process and compare the same stored records."""

import json
import subprocess
import sys

from sqlalchemy import insert, select
from sqlalchemy.orm import Session
from test_storage import database as database
from test_storage import seed

from app.models import comments, segments


def test_fresh_process_retains_content_and_search(database: Session):
    workspace, user = seed(database)
    segment = (
        database.execute(select(segments).where(segments.c.workspace_id == workspace))
        .mappings()
        .first()
    )
    database.execute(
        insert(comments).values(
            workspace_id=workspace,
            meeting_id=segment["meeting_id"],
            segment_id=segment["public_id"],
            author_id=user,
            body="Restart annotation",
        )
    )
    database.commit()
    sql = {
        "meetings": "SELECT id,title FROM meetings ORDER BY id",
        "tasks": "SELECT id,text,status FROM action_items ORDER BY id",
        "annotations": "SELECT id,body FROM comments ORDER BY id",
        "search": "SELECT rowid FROM search_documents_fts "
        "WHERE search_documents_fts MATCH 'review' ORDER BY rowid",
    }
    from sqlalchemy import text

    expected = {
        key: [list(row) for row in database.execute(text(query))] for key, query in sql.items()
    }
    database.close()
    # Both drivers report the real on-disk path; it is a disposable test fixture.
    engine = database.get_bind()
    with engine.connect() as connection:
        location = next(
            row[2] for row in connection.exec_driver_sql("PRAGMA database_list") if row[1] == "main"
        )
    driver = "libsql" if engine.url.drivername == "sqlite+workspace_libsql" else "sqlite"
    engine.dispose()
    code = """
import json,sys
from sqlalchemy import text
from app.db.engine import make_engine
from app.db.libsql import make_libsql_engine
engine = (make_libsql_engine(sys.argv[1]) if sys.argv[2] == 'libsql'
          else make_engine('sqlite:///' + sys.argv[1]))
with engine.connect() as connection:
    print(json.dumps({key: [list(row) for row in connection.execute(text(query))]
                      for key,query in json.loads(sys.argv[3]).items()}))
engine.dispose()
"""
    actual = subprocess.check_output(
        [sys.executable, "-c", code, location, driver, json.dumps(sql)], text=True
    )
    assert json.loads(actual) == expected
