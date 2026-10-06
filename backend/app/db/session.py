from collections.abc import Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.engine import engine


def get_db() -> Iterator[Session]:
    with Session(engine) as db:
        yield db


def begin_write(db: Session) -> None:
    # Reserving the writer before checking quotas prevents concurrent over-allocation.
    db.execute(text("BEGIN IMMEDIATE"))
