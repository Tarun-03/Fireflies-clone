from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from test_api import client as client
from test_api import session
from test_storage import database as database

from app.api.dependencies import Scope
from app.db.session import begin_write
from app.models import attendees, demo_sessions, idempotency_records, meetings, participants, users
from app.models.common import uid
from app.repositories.meetings import Filters, library
from app.services.maintenance import prune_expired


def test_library_byte_budget_paginates_without_omissions(
    client: TestClient, database: Session
) -> None:
    headers = session(client)
    owner = (
        database.execute(
            select(demo_sessions).where(demo_sessions.c.id == headers["X-Demo-Session"])
        )
        .mappings()
        .one()
    )
    scope = Scope(database, owner["workspace_id"], owner["user_id"], owner["id"])
    begin_write(database)
    people = [uid() for _ in range(100)]
    database.execute(
        insert(participants),
        [
            {"id": key, "workspace_id": scope.workspace_id, "display_name": "😀" * 120}
            for key in people
        ],
    )
    for _ in range(20):
        key = uid()
        database.execute(
            insert(meetings).values(
                id=key,
                workspace_id=scope.workspace_id,
                created_by_id=scope.user_id,
                title="Large metadata",
                occurred_at="2026-10-06T00:00:00+00:00",
                duration_ms=1000,
                source="manual",
            )
        )
        database.execute(
            insert(attendees),
            [
                {"workspace_id": scope.workspace_id, "meeting_id": key, "participant_id": person}
                for person in people
            ],
        )
    database.commit()
    first = library(scope, Filters(), 100, None)
    assert len(first.items) < 28 and first.has_more
    assert len(first.model_dump_json().encode()) < 1024 * 1024
    all_ids = [str(item.id) for item in first.items]
    cursor = first.next_cursor
    while cursor:
        page = library(scope, Filters(), 100, cursor)
        assert len(page.model_dump_json().encode()) < 1024 * 1024
        all_ids += [str(item.id) for item in page.items]
        cursor = page.next_cursor
    assert len(all_ids) == len(set(all_ids)) == 28


def test_expired_workspace_cleanup_preserves_active_workspace(
    client: TestClient, database: Session
) -> None:
    expired, active = session(client), session(client)
    record = (
        database.execute(
            select(demo_sessions).where(demo_sessions.c.id == expired["X-Demo-Session"])
        )
        .mappings()
        .one()
    )
    begin_write(database)
    database.execute(
        update(demo_sessions)
        .where(demo_sessions.c.id == record["id"])
        .values(expires_at="2000-01-01T00:00:00+00:00")
    )
    database.execute(
        insert(idempotency_records).values(
            workspace_id=record["workspace_id"],
            endpoint="test",
            key=str(uuid4()),
            body_hash="x",
            state="complete",
            expires_at="2000-01-01T00:00:00+00:00",
        )
    )
    assert prune_expired(database, expired_workspaces=True) == 1
    assert database.scalar(select(users.c.id).where(users.c.id == record["user_id"])) is not None
    assert prune_expired(database, apply=True, expired_workspaces=True) == 1
    database.commit()
    assert database.scalar(select(users.c.id).where(users.c.id == record["user_id"])) is None
    assert client.get("/api/v1/meetings", headers=expired).status_code == 401
    assert len(client.get("/api/v1/meetings", headers=active).json()["items"]) == 8


def test_null_nonnullable_mutations_and_whitespace_rejected(client: TestClient) -> None:
    headers = session(client)
    meeting = client.get("/api/v1/meetings", headers=headers).json()["items"][0]
    base = "/api/v1/meetings/" + meeting["id"]
    for payload in [{"title": None}, {"title": "   "}, {"duration_ms": None}]:
        assert (
            client.patch(base, headers=headers | {"If-Match": "1"}, json=payload).status_code == 422
        )
    task = client.get(base + "/action-items", headers=headers).json()["items"][0]
    for payload in [{"text": None}, {"status": None}, {"text": "   "}]:
        assert (
            client.patch(
                base + "/action-items/" + task["id"],
                headers=headers | {"If-Match": "1"},
                json=payload,
            ).status_code
            == 422
        )


def test_resuming_existing_session_does_not_exhaust_bootstrap_budget(client: TestClient) -> None:
    headers = session(client)
    for _ in range(25):
        assert client.post("/api/v1/demo/session", headers=headers).status_code == 200
    assert len(client.get("/api/v1/meetings", headers=headers).json()["items"]) == 8


def test_provider_failure_cooldown(monkeypatch) -> None:
    from app.services import provider_guard

    clock = [100.0]
    monkeypatch.setattr(provider_guard.time, "monotonic", lambda: clock[0])
    provider_guard.record_result(False)
    provider_guard.record_result(False)
    assert not provider_guard.cooling_down()
    provider_guard.record_result(False)
    assert provider_guard.cooling_down()
    clock[0] += 61
    assert not provider_guard.cooling_down()
