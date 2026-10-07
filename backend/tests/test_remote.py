import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from test_storage import database as database
from test_storage import seed

from alembic import command
from app.core.config import Settings, get_settings
from app.core.errors import DomainError
from app.core.limits import check_database_budget, check_storage, ensure_free_space
from app.db.engine import configured_engine
from app.db.libsql import call

TOKEN = "test-only-service-token-with-32-characters"


def settings(**values):
    return Settings(_env_file=None, internal_api_token=TOKEN, **values)


@pytest.mark.parametrize(
    "values",
    [
        {"turso_database_url": "libsql://test.turso.io"},
        {"turso_auth_token": "test-token"},
        {"turso_database_url": "http://test.turso.io", "turso_auth_token": "test-token"},
        {
            "turso_database_url": "libsql://test.turso.io?auth=secret",
            "turso_auth_token": "test-token",
        },
        {"turso_database_url": "libsql://localhost", "turso_auth_token": "test-token"},
        {"environment": "production", "allowed_hosts": "api.example.com"},
    ],
)
def test_invalid_remote_configuration_fails_closed(values):
    with pytest.raises(ValidationError):
        settings(**values)


def test_remote_engine_uses_https_and_separate_token(monkeypatch):
    import app.db.libsql as driver

    calls = []
    monkeypatch.setattr(driver, "make_libsql_engine", lambda *a: calls.append(a))
    config = settings(
        environment="production",
        allowed_hosts="api.example.com",
        turso_database_url="libsql://test.turso.io",
        turso_auth_token="private-test-token",
    )
    configured_engine(config)
    assert calls == [("https://test.turso.io", "private-test-token")]
    assert "private-test-token" not in repr(config)


def test_remote_skips_host_disk_checks_but_keeps_application_quota(database: Session, monkeypatch):
    from app.core import limits

    workspace, _ = seed(database)
    monkeypatch.setattr(get_settings(), "turso_database_url", "libsql://test.turso.io")
    monkeypatch.setattr(
        limits.shutil, "disk_usage", lambda *a: pytest.fail("Remote checked local disk")
    )
    ensure_free_space()
    check_database_budget(None)  # Remote mode must not issue physical page-allocation PRAGMAs.
    check_storage(database, workspace)
    monkeypatch.setattr(get_settings(), "max_meetings", 8)
    with pytest.raises(DomainError) as error:
        check_storage(database, workspace)
    assert error.value.code == "quota"


def test_migration_downgrade_and_upgrade(database: Session):
    engine = database.get_bind()
    database.close()
    with engine.connect() as connection:
        config = Config("alembic.ini")
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert inspect(connection).get_table_names() == ["alembic_version"]
        connection.rollback()
        command.upgrade(config, "head")
        command.check(config)
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1


def test_libsql_error_redaction():
    def unavailable():
        raise ValueError("network error with private-token and connection URL")

    with pytest.raises(sqlite3.OperationalError) as error:
        call(unavailable)
    assert "private-token" not in str(error.value)


def test_remote_file_backup_is_refused(monkeypatch, tmp_path: Path):
    from scripts.storage import main

    monkeypatch.setattr(get_settings(), "turso_database_url", "libsql://test.turso.io")
    destination = tmp_path / "backup.db"
    monkeypatch.setattr("sys.argv", ["storage", "backup", "--destination", str(destination)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert not destination.exists()


def test_real_database_compatibility_probe(database: Session):
    from sqlalchemy import select

    from app.models import workspaces
    from scripts.verify_database import verify

    workspace = verify(database)
    assert database.scalar(select(workspaces.c.id).where(workspaces.c.id == workspace)) is None
