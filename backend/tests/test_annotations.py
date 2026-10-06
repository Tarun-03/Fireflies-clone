from uuid import uuid4

from fastapi.testclient import TestClient
from test_api import client as client
from test_api import session
from test_storage import database as database


def test_annotation_lifecycle_scoping_and_unicode(client: TestClient) -> None:
    one, two = session(client), session(client)
    meeting = client.post(
        "/api/v1/meetings",
        headers=one | {"Idempotency-Key": str(uuid4())},
        json={
            "title": "Unicode annotations",
            "occurred_at": "2026-10-06T00:00:00Z",
            "duration_ms": 10000,
            "segments": [
                {"speaker": "Sam", "start_ms": 0, "end_ms": 10000, "text": "A😀é café launch."}
            ],
        },
    ).json()
    base = "/api/v1/meetings/" + meeting["id"]
    segment = client.get(base + "/transcript", headers=one).json()["items"][0]
    other = client.get("/api/v1/meetings", headers=two).json()["items"][0]
    foreign_segment = client.get(f"/api/v1/meetings/{other['id']}/transcript", headers=two).json()[
        "items"
    ][0]
    assert (
        client.post(
            base + "/comments",
            headers=one,
            json={
                "segment_id": foreign_segment["public_id"],
                "segment_version": 1,
                "body": "Forged source",
            },
        ).status_code
        == 404
    )
    selection = {
        "segment_id": segment["public_id"],
        "segment_version": 1,
        "start_offset": 1,
        "end_offset": 4,
        "selected_text": "😀é",
        "note": "Unicode note",
        "color": "amber",
    }
    highlight = client.post(base + "/highlights", headers=one, json=selection)
    assert highlight.status_code == 201, highlight.text
    assert (
        client.get(base + "/transcript", headers=one).json()["items"][0]["highlights"][0][
            "end_offset"
        ]
        == 4
    )
    assert (
        client.post(
            base + "/highlights", headers=one, json=selection | {"selected_text": "wrong"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            base + "/highlights", headers=one, json=selection | {"end_offset": 999}
        ).status_code
        == 422
    )
    assert (
        client.post(
            base + "/highlights", headers=one, json=selection | {"segment_version": 9}
        ).status_code
        == 409
    )
    comment = client.post(
        base + "/comments",
        headers=one,
        json={
            "segment_id": segment["public_id"],
            "segment_version": 1,
            "body": "Check this launch claim.",
        },
    )
    assert comment.status_code == 201, comment.text
    clip = client.post(
        base + "/soundbites",
        headers=one,
        json={"title": "Launch excerpt", "start_ms": 0, "end_ms": 1000},
    )
    assert clip.status_code == 201, clip.text
    assert (
        client.post(
            base + "/soundbites",
            headers=one,
            json={"title": "Too long", "start_ms": 0, "end_ms": 20000},
        ).status_code
        == 422
    )
    for kind, created in [("comments", comment), ("highlights", highlight), ("soundbites", clip)]:
        assert client.get(base + "/" + kind, headers=two).status_code == 404
        assert (
            client.delete(
                base + "/" + kind + "/" + created.json()["id"], headers=two | {"If-Match": "1"}
            ).status_code
            == 404
        )
    export = client.get(base + "/soundbites/" + clip.json()["id"] + "/export", headers=one)
    assert export.status_code == 200 and "[00:00:00] Sam: A😀é café launch." in export.text
    assert (
        client.get(base + "/soundbites/" + clip.json()["id"] + "/export", headers=two).status_code
        == 404
    )
    edited = client.patch(
        base + "/comments/" + comment.json()["id"],
        headers=one | {"If-Match": "1"},
        json={"body": "Revised comment"},
    )
    assert edited.status_code == 200
    segment_url = base + "/segments/" + segment["public_id"]
    patch = {"text": "Changed transcript content.", "start_ms": 0, "end_ms": 10000}
    assert client.patch(segment_url, headers=one | {"If-Match": "1"}, json=patch).status_code == 409
    assert (
        client.patch(
            segment_url,
            headers=one | {"If-Match": "1"},
            json=patch | {"remove_affected_highlights": True},
        ).status_code
        == 200
    )
    assert client.get(base + "/highlights", headers=one).json()["items"] == []
    assert (
        client.get(base + "/comments", headers=one).json()["items"][0]["body"] == "Revised comment"
    )
    assert (
        client.delete(
            base + "/comments/" + comment.json()["id"], headers=one | {"If-Match": "1"}
        ).status_code
        == 409
    )
    assert (
        client.delete(
            base + "/comments/" + comment.json()["id"], headers=one | {"If-Match": "2"}
        ).status_code
        == 204
    )
    assert (
        client.delete(
            base + "/soundbites/" + clip.json()["id"], headers=one | {"If-Match": "1"}
        ).status_code
        == 204
    )
