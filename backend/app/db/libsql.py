"""SQLAlchemy bridge for Turso's libsql client (not the separate Turso engine).

libsql 0.1.11 raises ValueError for SQL failures rather than DBAPI subclasses.
Normalize those failures so existing rollback and HTTP error handling applies.
"""

import sqlite3
from collections.abc import Callable
from typing import Any

import libsql  # type: ignore[import-untyped]
from sqlalchemy import create_engine
from sqlalchemy.dialects import registry
from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

_TRIGGER_ERRORS = (
    "duration truncates",
    "highlight requires explicit invalidation",
    "interval exceeds duration",
    "highlight does not match text",
)


class LibsqlDialect(SQLiteDialect_pysqlite):
    supports_statement_cache = True

    def on_connect(self) -> Callable[[Any], None]:
        # libsql has no Python UDF API; our queries use built-in SQL/FTS functions.
        return lambda connection: None


registry.register("sqlite.workspace_libsql", __name__, "LibsqlDialect")


def call(function: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except (ValueError, libsql.Error) as exc:
        message = str(exc).lower()
        if "constraint" in message or any(value in message for value in _TRIGGER_ERRORS):
            raise sqlite3.IntegrityError("Database constraint rejected the change") from None
        # Do not propagate driver messages: remote errors may contain connection details.
        raise sqlite3.OperationalError("libSQL operation failed") from None


class Cursor:
    def __init__(self, raw: Any) -> None:
        self.raw = raw

    def __getattr__(self, name: str) -> Any:
        value = getattr(self.raw, name)
        return (lambda *a, **kw: call(value, *a, **kw)) if callable(value) else value

    def execute(self, *args: Any, **kwargs: Any) -> "Cursor":
        call(self.raw.execute, *args, **kwargs)
        return self

    def executemany(self, *args: Any, **kwargs: Any) -> "Cursor":
        call(self.raw.executemany, *args, **kwargs)
        return self


class Connection:
    def __init__(self, raw: Any) -> None:
        self.raw = raw

    def cursor(self) -> Cursor:
        return Cursor(call(self.raw.cursor))

    def __getattr__(self, name: str) -> Any:
        value = getattr(self.raw, name)
        return (lambda *a, **kw: call(value, *a, **kw)) if callable(value) else value


def make_libsql_engine(database: str, token: str = "") -> Engine:
    def connect() -> Connection:
        raw = call(libsql.connect, database, auth_token=token, isolation_level="")
        connection = Connection(raw)
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA foreign_keys")
        if cursor.fetchone()[0] != 1:
            connection.close()
            raise sqlite3.OperationalError("Foreign key enforcement is required")
        cursor.close()
        return connection

    return create_engine(
        "sqlite+workspace_libsql://", creator=connect, poolclass=NullPool, hide_parameters=True
    )
