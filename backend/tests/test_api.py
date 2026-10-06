from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_storage import database as database

TOKEN = "Bearer test-only-service-token-with-32-characters"


@pytest.fixture
def client(database: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    import app.api.dependencies as dependencies
    import app.api.workspace as workspace
    from app.main import app

    monkeypatch.setattr(dependencies, "engine", database.get_bind())
    monkeypatch.setattr(workspace, "engine", database.get_bind())
    from app.core.limits import _requests

    _requests.clear()
    with TestClient(app) as client:
        yield client


def session(client: TestClient) -> dict[str, str]:
    headers = {"Authorization": TOKEN, "X-Demo-Session": str(uuid4())}
    response = client.post("/api/v1/demo/session", headers=headers)
    assert response.status_code == 200, response.text
    return headers


def test_service_auth_and_isolation(client: TestClient) -> None:
    assert client.get("/api/v1/meetings").status_code == 401
    one = session(client)
    two = session(client)
    response = client.get("/api/v1/meetings", headers=one)
    assert response.status_code == 200, response.text
    meeting = response.json()["items"][0]
    for method in ["get", "delete", "patch"]:
        kwargs = {"json": {"title": "Changed"}} if method == "patch" else {}
        result = getattr(client, method)(
            f"/api/v1/meetings/{meeting['id']}", headers=two | {"If-Match": "1"}, **kwargs
        )
        assert result.status_code == 404, result.text
    assert (
        client.get(f"/api/v1/meetings/{meeting['id']}/action-items", headers=two).status_code == 404
    )
    assert "workspace_id" not in meeting


def test_versions_unknown_fields_and_tags(client: TestClient) -> None:
    headers = session(client)
    meeting = client.get("/api/v1/meetings", headers=headers).json()["items"][0]
    url = f"/api/v1/meetings/{meeting['id']}"
    assert client.patch(url, headers=headers, json={"title": "Changed"}).status_code == 428
    assert (
        client.patch(
            url, headers=headers | {"If-Match": "0"}, json={"title": "Changed"}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            url, headers=headers | {"If-Match": "1"}, json={"workspace_id": str(uuid4())}
        ).status_code
        == 422
    )
    changed = client.patch(url, headers=headers | {"If-Match": "1"}, json={"title": "Changed"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 2
    tag = client.post("/api/v1/tags", headers=headers, json={"name": "Review", "color": "green"})
    assert tag.status_code == 201, tag.text
    assert (
        client.put(
            url + "/tags", headers=headers | {"If-Match": "2"}, json={"tag_ids": [tag.json()["id"]]}
        ).status_code
        == 200
    )
    assert (
        client.delete(
            "/api/v1/tags/" + tag.json()["id"], headers=headers | {"If-Match": "1"}
        ).status_code
        == 204
    )
    assert client.get(url, headers=headers).json()["tags"] == []


def test_create_idempotency_and_task_lifecycle(client: TestClient) -> None:
    headers = session(client) | {"Idempotency-Key": str(uuid4())}
    payload = {
        "title": "Release review",
        "occurred_at": "2026-10-06T12:00:00Z",
        "duration_ms": 60000,
        "participants": [{"display_name": "Sam"}],
        "segments": [
            {
                "speaker": "Sam",
                "start_ms": 0,
                "end_ms": 60000,
                "text": "I will verify the release checklist.",
            }
        ],
    }
    response = client.post("/api/v1/meetings", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    repeated = client.post("/api/v1/meetings", headers=headers, json=payload)
    assert repeated.json()["id"] == response.json()["id"]
    payload["title"] = "Different"
    assert client.post("/api/v1/meetings", headers=headers, json=payload).status_code == 409
    url = f"/api/v1/meetings/{response.json()['id']}/action-items"
    task = client.get(url, headers=headers).json()["items"][0]
    complete = client.patch(
        url + "/" + task["id"], headers=headers | {"If-Match": "1"}, json={"status": "completed"}
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["completed_at"] is not None
    reopen = client.patch(
        url + "/" + task["id"], headers=headers | {"If-Match": "2"}, json={"status": "open"}
    )
    assert reopen.json()["completed_at"] is None


def test_pagination_and_filters(client: TestClient) -> None:
    headers = session(client)
    ids: list[str] = []
    cursor = None
    for _ in range(4):
        params = {"limit": "2", "sort": "recent"}
        if cursor:
            params["cursor"] = cursor
        result = client.get("/api/v1/meetings", headers=headers, params=params).json()
        ids.extend(item["id"] for item in result["items"])
        cursor = result["next_cursor"]
    assert len(ids) == len(set(ids)) == 8
    assert cursor is None
    assert len(client.get("/api/v1/meetings?q=standup", headers=headers).json()["items"]) == 1
    assert client.get("/api/v1/meetings?cursor=not-valid", headers=headers).status_code == 422


def test_preferences_and_nested_substitution(client: TestClient) -> None:
    headers = session(client)
    current = client.get("/api/v1/me", headers=headers)
    assert current.status_code == 200, current.text
    result = client.patch(
        "/api/v1/me/preferences",
        headers=headers | {"If-Match": "1"},
        json={"theme": "dark", "timezone": "UTC"},
    )
    assert result.status_code == 200, result.text
    rows = client.get("/api/v1/meetings", headers=headers).json()["items"]
    task = client.get(f"/api/v1/meetings/{rows[0]['id']}/action-items", headers=headers).json()[
        "items"
    ][0]
    assert (
        client.delete(
            f"/api/v1/meetings/{rows[1]['id']}/action-items/{task['id']}",
            headers=headers | {"If-Match": "1"},
        ).status_code
        == 404
    )


def test_request_limit_and_naive_dates(client: TestClient) -> None:
    headers = session(client)
    response = client.post(
        "/api/v1/meetings",
        headers=headers | {"Content-Type": "application/json"},
        content=(b"x" * 1024 * 1024 for _ in range(4)),
    )
    assert response.status_code == 413
    assert "error" in response.json()
    assert (
        client.get("/api/v1/meetings?after=2026-10-06T00:00:00", headers=headers).status_code == 422
    )
    assert client.get("/api/v1/meetings?limit=101", headers=headers).status_code == 422
    assert (
        client.get(
            "/api/v1/meetings", headers=headers | {"Authorization": "Bearer wrong"}
        ).status_code
        == 401
    )


def test_workspace_quota(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    config = get_settings()
    monkeypatch.setattr(config, "max_workspaces", 1)
    session(client)
    headers = {"Authorization": TOKEN, "X-Demo-Session": str(uuid4())}
    assert client.post("/api/v1/demo/session", headers=headers).status_code == 429
