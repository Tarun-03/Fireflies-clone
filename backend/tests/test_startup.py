from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from test_api import client as client
from test_storage import database as database

from app.core.config import get_settings
from scripts.start import prepare


def test_runtime_migrations_are_repeatable(tmp_path: Path, monkeypatch) -> None:
    import sqlite3

    location = tmp_path / "mounted.db"
    monkeypatch.setattr(get_settings(), "database_url", "sqlite:///" + str(location))
    prepare()
    prepare()
    with sqlite3.connect(location) as connection:
        assert connection.execute("SELECT count(*) FROM workspaces").fetchone() == (0,)
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_readiness_rejects_outdated_schema(
    client: TestClient, database: Session, monkeypatch
) -> None:
    import app.main as main

    monkeypatch.setattr(main, "engine", database.get_bind())
    assert client.get("/health/ready").status_code == 200
    database.execute(text("UPDATE alembic_version SET version_num='outdated'"))
    database.commit()
    response = client.get("/health/ready")
    assert response.status_code == 503 and response.json() == {"status": "unavailable"}
