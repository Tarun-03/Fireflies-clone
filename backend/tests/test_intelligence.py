import asyncio
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from test_api import client as client
from test_api import session
from test_storage import database as database

from app.core.config import get_settings
from app.core.errors import DomainError
from app.models import meetings
from app.schemas.intelligence import Evidence, GeneratedSummary, GeneratedTask
from app.schemas.notebook import Segment
from app.services import intelligence


def evidence() -> list[Segment]:
    return [
        Segment(
            public_id=uuid4(),
            speaker_id=uuid4(),
            ordinal=0,
            start_ms=0,
            end_ms=10000,
            text="I will verify the café launch.",
            version=1,
            speaker_name="Sam",
            stable_color_key=0,
        )
    ]


def test_provider_adapter_validates_structured_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = evidence()
    answer = GeneratedSummary(
        overview="A launch commitment was recorded.",
        key_points=[Evidence(segment_id=str(rows[0].public_id), text="Launch verification")],
        decisions=[],
        tasks=[GeneratedTask(segment_id=str(rows[0].public_id), text=rows[0].text)],
    )
    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.responses = self

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            pass

        async def parse(self, **kwargs: Any) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(output_parsed=answer)

    monkeypatch.setattr(intelligence, "AsyncOpenAI", FakeClient)
    monkeypatch.setattr(get_settings(), "llm_model", "test-structured-model")
    monkeypatch.setattr(get_settings(), "openai_api_key", SecretStr("test-only-key"))
    result = asyncio.run(intelligence.provider_summary(rows, str(uuid4()), 1))
    assert result == answer
    assert captured["base_url"] == "https://api.openai.com/v1"
    assert captured["timeout"] == 30 and captured["max_retries"] == 0
    assert captured["max_output_tokens"] == 4000 and captured["store"] is False
    assert "tools" not in captured and "test-only-key" not in captured["input"]
    assert "untrusted data" in captured["instructions"]


@pytest.mark.parametrize(
    "failure", ["timeout", "invalid_json", "foreign_source", "invented_task", "duplicate"]
)
def test_invalid_provider_output_falls_back(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    rows = evidence()
    monkeypatch.setattr(get_settings(), "llm_provider", "openai")

    async def bad(*args: Any) -> GeneratedSummary:
        if failure == "timeout":
            raise TimeoutError()
        if failure == "invalid_json":
            raise ValueError("invalid JSON")
        source = str(uuid4()) if failure == "foreign_source" else str(rows[0].public_id)
        point = Evidence(segment_id=source, text="Launch")
        result = GeneratedSummary(
            overview="Launch",
            key_points=[point, point] if failure == "duplicate" else [point],
            decisions=[],
            tasks=[GeneratedTask(segment_id=source, text="I will deploy tomorrow.")]
            if failure == "invented_task"
            else [],
        )
        return intelligence.validate_sources(result, rows)

    monkeypatch.setattr(intelligence, "provider_summary", bad)
    result, provider, notice = asyncio.run(
        intelligence.generate_summary(rows, str(uuid4()), 1, "openai")
    )
    assert provider == "extractive" and notice
    assert result.tasks[0].text == rows[0].text


def test_extractive_does_not_contact_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    async def never(*args: Any) -> GeneratedSummary:
        raise AssertionError("Provider must not run")

    monkeypatch.setattr(intelligence, "provider_summary", never)
    result, provider, notice = asyncio.run(
        intelligence.generate_summary(evidence(), str(uuid4()), 1, "extractive")
    )
    assert provider == "extractive" and notice is None and result.tasks


def test_disconnect_cancels_operation() -> None:
    class Disconnected:
        async def is_disconnected(self) -> bool:
            return True

    async def slow() -> int:
        await asyncio.sleep(30)
        return 1

    with pytest.raises(DomainError) as error:
        asyncio.run(intelligence.while_connected(Disconnected(), slow()))  # type: ignore[arg-type]
    assert error.value.status == 499


def test_regeneration_preserves_work_and_replays(client: TestClient) -> None:
    headers = session(client)
    meeting = client.get("/api/v1/meetings", headers=headers).json()["items"][0]
    base = f"/api/v1/meetings/{meeting['id']}"
    summary = client.get(base + "/summary", headers=headers).json()
    tasks = client.get(base + "/action-items", headers=headers).json()["items"]
    completed = tasks[0]
    assert (
        client.patch(
            base + "/action-items/" + completed["id"],
            headers=headers | {"If-Match": "1"},
            json={"status": "completed"},
        ).status_code
        == 200
    )
    edited = tasks[1]
    assert (
        client.patch(
            base + "/action-items/" + edited["id"],
            headers=headers | {"If-Match": "1"},
            json={"text": "My edited commitment"},
        ).status_code
        == 200
    )
    manual = client.post(
        base + "/action-items",
        headers=headers,
        json={
            "text": "Manual plan",
            "due_date": "2026-10-20",
            "assignee_participant_id": meeting["participants"][0]["id"],
        },
    ).json()
    assert (
        client.patch(
            base + "/summary",
            headers=headers | {"If-Match": str(summary["version"])},
            json={"notes": "Keep my private notes"},
        ).status_code
        == 200
    )
    generated_headers = headers | {"If-Match": "2", "Idempotency-Key": str(uuid4())}
    response = client.post(
        base + "/summary/regenerate", headers=generated_headers, json={"mode": "extractive"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["notes"] == "Keep my private notes"
    repeated = client.post(
        base + "/summary/regenerate", headers=generated_headers, json={"mode": "extractive"}
    )
    assert repeated.json() == response.json()
    after = client.get(base + "/action-items", headers=headers).json()["items"]
    assert {completed["id"], edited["id"], manual["id"]} <= {t["id"] for t in after}
    assert next(t for t in after if t["id"] == manual["id"])["due_date"] == "2026-10-20"
    assert any(t["text"] == "My edited commitment" for t in after)
    assert all(
        t["assignee_participant_id"] is None and t["due_date"] is None
        for t in after
        if t["origin"] == "extracted" and not t["user_edited"] and t["status"] == "open"
    )
    foreign = session(client)
    assert (
        client.post(
            base + "/summary/regenerate",
            headers=foreign | {"If-Match": "3", "Idempotency-Key": str(uuid4())},
            json={"mode": "extractive"},
        ).status_code
        == 404
    )


def test_transcript_change_during_generation_rolls_back(
    client: TestClient, database: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.api.summary as api_summary

    headers = session(client)
    meeting = client.get("/api/v1/meetings", headers=headers).json()["items"][0]
    base = f"/api/v1/meetings/{meeting['id']}"
    original = client.get(base + "/summary", headers=headers).json()

    async def changing(rows: list[Segment], *args: Any) -> tuple[GeneratedSummary, str, None]:
        # A second writer can commit while generation is running: no provider-duration DB lock.
        with Session(database.get_bind()) as concurrent:
            concurrent.execute(
                update(meetings).where(meetings.c.id == meeting["id"]).values(transcript_revision=2)
            )
            concurrent.commit()
        return intelligence.extractive(rows), "extractive", None

    monkeypatch.setattr(api_summary, "generate_summary", changing)
    result = client.post(
        base + "/summary/regenerate",
        headers=headers | {"If-Match": "1", "Idempotency-Key": str(uuid4())},
        json={"mode": "extractive"},
    )
    assert result.status_code == 409, result.text
    after = client.get(base + "/summary", headers=headers).json()
    assert after["version"] == original["version"] and after["stale"]
    assert (
        database.scalar(
            select(meetings.c.transcript_revision).where(meetings.c.id == meeting["id"])
        )
        == 2
    )
