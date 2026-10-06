import base64
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_api import client as client
from test_api import session
from test_storage import database as database

from app.core.errors import DomainError
from app.schemas.imports import ImportRequest
from app.services.parsers import parse


def test_txt_bom_crlf_continuations_and_estimates() -> None:
    parsed = parse(
        ImportRequest(
            format="txt",
            content=(
                "\ufeff[00:00] Zoë: We decided to use café 😀.\r\n"
                "A continuation.\r\n[00:30] Lee: I will write it."
            ),
        )
    )
    assert len(parsed.segments) == 2
    assert "\nA continuation." in parsed.segments[0].text
    assert parsed.segments[0].end_ms == 30000
    assert parsed.estimated_timing
    plain = parse(ImportRequest(format="txt", content="Someone will review this."))
    assert plain.segments[0].speaker == "Unknown speaker"
    assert plain.duration_ms == 1600


def test_vtt_multiline_voice_markup_overlap_metadata() -> None:
    parsed = parse(
        ImportRequest(
            format="vtt",
            content=(
                "WEBVTT\n\nNOTE synthetic\nignored\n\ncue-1\n00:00.000 --> 00:02.000\n"
                "<v Zoë><b>Café</b> 😀\n&amp; tea.</v>\n\n"
                "00:01.500 --> 00:03.000\n<v Lee>Yes.</v>"
            ),
        )
    )
    assert parsed.segments[0].speaker == "Zoë"
    assert parsed.segments[0].text == "Café 😀\n& tea."
    assert parsed.segments[1].start_ms < parsed.segments[0].end_ms
    assert not parsed.estimated_timing


@pytest.mark.parametrize(
    "format,content",
    [
        ("txt", ""),
        ("txt", "\x00binary"),
        ("txt", "<html><body>not a transcript</body></html>"),
        ("txt", "[00:99] Sam: Invalid."),
        ("txt", "[00:01] Sam: First.\n[00:00] Lee: Earlier."),
        ("txt", "[00:01] Sam: First.\nLee: Missing time."),
        ("vtt", "00:00:00.000 --> 00:00:01.000\nMissing header"),
        ("vtt", "WEBVTT\n\n00:00.000 --> 00:00.000\nEmpty interval."),
        ("vtt", "WEBVTT\n\n00:00.000 --> 00:01.000\n<b></b>"),
        ("json", "{"),
        ("json", '{"schema_version":1,"segments":[],"secret":1}'),
        ("json", '{"schema_version":1,"schema_version":1,"segments":[]}'),
        ("json", '{"schema_version":NaN,"segments":[]}'),
        ("json", "[" * 100 + "0" + "]" * 100),
    ],
)
def test_rejected_content(format: str, content: str) -> None:
    with pytest.raises(DomainError):
        parse(ImportRequest.model_validate({"format": format, "content": content}))


@pytest.mark.parametrize(
    "name",
    [
        "../meeting.txt",
        "meeting.txt.exe",
        "meeting.vtt.txt",
        "folder\\meeting.txt",
        "meeting\n.txt",
    ],
)
def test_filename_attacks(name: str) -> None:
    with pytest.raises(DomainError):
        parse(ImportRequest(format="txt", filename=name, content="Speaker: Safe content."))


def test_non_utf8_and_limits() -> None:
    with pytest.raises(DomainError):
        parse(ImportRequest(format="txt", content_base64=base64.b64encode(b"\xff\xfe").decode()))
    with pytest.raises(DomainError) as error:
        parse(ImportRequest(format="txt", content="😀" * 600000))
    assert error.value.status == 413


def test_import_idempotency_preview_ack_and_edit(client: TestClient) -> None:
    headers = session(client)
    body = {
        "format": "txt",
        "title": "Unicode import",
        "content": "Zoë: I will update the café 😀 checklist.",
    }
    preview = client.post("/api/v1/meetings/import/preview", headers=headers, json=body)
    assert preview.status_code == 200, preview.text
    assert preview.json()["estimated_timing"]
    key_headers = headers | {"Idempotency-Key": str(uuid4())}
    assert client.post("/api/v1/meetings/import", headers=key_headers, json=body).status_code == 422
    body["acknowledge_estimated"] = True
    created = client.post("/api/v1/meetings/import", headers=key_headers, json=body)
    assert created.status_code == 201, created.text
    assert (
        client.post("/api/v1/meetings/import", headers=key_headers, json=body).json()["id"]
        == created.json()["id"]
    )
    base = "/api/v1/meetings/" + created.json()["id"]
    segment = client.get(base + "/transcript", headers=headers).json()["items"][0]
    url = base + "/segments/" + segment["public_id"]
    update = {
        "text": "Zoë will inspect the café 😀 checklist.",
        "start_ms": 0,
        "end_ms": segment["end_ms"],
    }
    second = session(client)
    assert client.patch(url, headers=second | {"If-Match": "1"}, json=update).status_code == 404
    assert client.patch(url, headers=headers | {"If-Match": "1"}, json=update).status_code == 200
    assert client.patch(url, headers=headers | {"If-Match": "1"}, json=update).status_code == 409
    assert client.get(base + "/summary", headers=headers).json()["stale"]
    assert client.get(base + "/transcript/search?q=inspect", headers=headers).json()["total"] == 1
    assert client.delete(url, headers=headers | {"If-Match": "2"}).status_code == 204
    assert client.get(base + "/transcript/search?q=inspect", headers=headers).json()["total"] == 0


@pytest.mark.parametrize("extension", ["txt", "vtt", "json"])
def test_downloadable_examples(client: TestClient, extension: str) -> None:
    headers = session(client) | {"Idempotency-Key": str(uuid4())}
    raw = (
        Path(__file__).parents[2] / "frontend" / "public" / "examples" / f"transcript.{extension}"
    ).read_bytes()
    result = client.post(
        "/api/v1/meetings/import",
        headers=headers,
        json={
            "format": extension,
            "filename": f"Example.{extension.upper()}",
            "content_base64": base64.b64encode(raw).decode(),
            "acknowledge_estimated": True,
        },
    )
    assert result.status_code == 201, result.text
    base = "/api/v1/meetings/" + result.json()["id"]
    assert len(client.get(base + "/transcript", headers=headers).json()["items"]) == 3


def test_json_types_unknown_fields_and_bounds() -> None:
    document = {
        "schema_version": 1,
        "duration_ms": 1000,
        "segments": [{"speaker": "Sam", "start_ms": 0, "end_ms": 2000, "text": "Content"}],
    }
    with pytest.raises(DomainError):
        parse(ImportRequest(format="json", content=json.dumps(document)))
    document.pop("duration_ms")
    document["segments"][0]["start_ms"] = "0"  # type: ignore[index]
    with pytest.raises(DomainError):
        parse(ImportRequest(format="json", content=json.dumps(document)))


def test_create_rollback_on_foreign_tag(client: TestClient) -> None:
    one, two = session(client), session(client)
    tag = client.get("/api/v1/tags", headers=two).json()["items"][0]["id"]
    result = client.post(
        "/api/v1/meetings/import",
        headers=one | {"Idempotency-Key": str(uuid4())},
        json={
            "format": "txt",
            "content": "Sam: I will check the notes.",
            "tag_ids": [tag],
            "acknowledge_estimated": True,
        },
    )
    assert result.status_code == 404
    assert len(client.get("/api/v1/meetings", headers=one).json()["items"]) == 8
