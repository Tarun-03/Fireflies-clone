"""Bounded multi-row inserts avoid a network request per transcript turn."""

from typing import Any

from sqlalchemy import Table, insert
from sqlalchemy.orm import Session


def insert_rows(db: Session, table: Table, rows: list[dict[str, Any]]) -> None:
    for offset in range(0, len(rows), 40):
        db.execute(insert(table).values(rows[offset : offset + 40]))
