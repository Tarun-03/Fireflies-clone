"""Operator-only backup, restore, index repair, and synthetic session creation."""

import argparse
import sqlite3
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import engine
from app.db.session import begin_write
from app.services.seed import bootstrap


def validate(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
        raise RuntimeError("Database integrity check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Database foreign key check failed")


def backup(source: Path, destination: Path) -> None:
    if destination.exists():
        raise ValueError("Backup destination must be new")
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as origin:
        with sqlite3.connect(destination) as target:
            origin.backup(target)
            validate(target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["backup", "restore", "rebuild-search", "seed"])
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--session", type=UUID)
    args = parser.parse_args()
    database = Path(get_settings().database_url.removeprefix("sqlite:///"))
    if args.command == "backup":
        if args.destination is None:
            parser.error("--destination is required")
        backup(database, args.destination)
    elif args.command == "restore":
        if args.source is None or args.destination is None:
            parser.error("--source and a new --destination are required; stop the server first")
        backup(args.source, args.destination)
    elif args.command == "rebuild-search":
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO search_documents_fts(search_documents_fts) VALUES('rebuild')")
            )
    else:
        if args.session is None:
            parser.error("--session UUID is required")
        with Session(engine) as db:
            begin_write(db)
            bootstrap(db, str(args.session))
            db.commit()
    print("Storage operation completed")


if __name__ == "__main__":
    main()
