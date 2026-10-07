import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import ConnectionPoolEntry

from app.core.config import Settings, get_settings


def make_engine(url: str) -> Engine:
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 5})

    @event.listens_for(engine, "connect")
    def configure(connection: sqlite3.Connection, record: ConnectionPoolEntry) -> None:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA synchronous=FULL")

    return engine


def configured_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    if settings.remote_database:
        from app.db.libsql import make_libsql_engine

        # Remote-only HTTPS connection. No embedded replica or local database file.
        endpoint = "https://" + settings.turso_database_url.removeprefix("libsql://").rstrip("/")
        return make_libsql_engine(endpoint, settings.turso_auth_token.get_secret_value())
    return make_engine(settings.database_url)


engine = configured_engine()
