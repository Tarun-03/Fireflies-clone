from uuid import uuid4

from fastapi.testclient import TestClient
from test_api import client as client
from test_api import session
from test_storage import database as database


def test_notebook_scope_search_and_notes(client: TestClient) -> None:
    one, two = session(client), session(client)
    meetings = client.get("/api/v1/meetings", headers=one).json()["items"]
    base = f"/api/v1/meetings/{meetings[0]['id']}"
    for suffix in [
        "transcript",
        "timeline",
        "transcript/window",
        "transcript/search?q=a",
        "summary",
        "chapters",
    ]:
        assert client.get(base + "/" + suffix, headers=two).status_code == 404
    page = client.get(base + "/transcript?limit=3", headers=one).json()
    assert len(page["items"]) == 3 and page["next_cursor"] == 3
    target = page["items"][2]
    result = client.get(base + f"/transcript/window?segment_id={target['public_id']}", headers=one)
    assert target["public_id"] in [s["public_id"] for s in result.json()["items"]]
    assert (
        client.get(base + f"/transcript/window?segment_id={uuid4()}", headers=one).status_code
        == 404
    )
    query = target["text"].split()[0]
    results = client.get(base + "/transcript/search", params={"q": query}, headers=one).json()
    assert results["total"] > 0
    assert all(hit["ranges"] for hit in results["items"])
    assert client.get(base + "/transcript/search?q=%22%20OR%20*", headers=one).status_code == 200
    notes = client.get(base + "/summary", headers=one).json()
    changed = client.patch(
        base + "/summary",
        headers=one | {"If-Match": str(notes["version"])},
        json={"notes": "Review 😀 café notes"},
    )
    assert changed.status_code == 200, changed.text
    assert client.get(base + "/summary", headers=one).json()["notes"] == "Review 😀 café notes"
    assert (
        client.patch(
            base + "/summary",
            headers=one | {"If-Match": str(notes["version"])},
            json={"notes": "stale"},
        ).status_code
        == 409
    )


def test_large_transcript_window(client: TestClient) -> None:
    headers = session(client) | {"Idempotency-Key": str(uuid4())}
    payload = {
        "title": "Long synthetic timing test",
        "occurred_at": "2026-10-06T00:00:00Z",
        "duration_ms": 3000000,
        "segments": [
            {
                "speaker": "Test speaker",
                "start_ms": i * 1000,
                "end_ms": i * 1000 + 900,
                "text": f"Distinct turn {i}: synthetic timing validation.",
            }
            for i in range(3000)
        ],
    }
    created = client.post("/api/v1/meetings", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    base = f"/api/v1/meetings/{created.json()['id']}"
    index = client.get(base + "/timeline", headers=headers)
    assert len(index.json()) == 3000
    assert len(index.content) < 1024 * 1024
    window = client.get(base + "/transcript/window?at_ms=2980500", headers=headers)
    assert len(window.json()["items"]) <= 60
    assert any(s["ordinal"] == 2980 for s in window.json()["items"])
    assert len(window.content) < 512 * 1024
    library = client.get("/api/v1/meetings", headers=headers).json()
    assert "segments" not in library["items"][0]
