"""Create or verify a synthetic backend restart probe; state includes a private session ID."""

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["before", "after"])
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    if args.phase == "before" and args.state.exists():
        parser.error("Choose a new state file to preserve previous evidence.")
    state = (
        {"session": str(uuid4())} if args.phase == "before" else json.loads(args.state.read_text())
    )
    headers = {
        "Authorization": "Bearer " + get_settings().internal_api_token.get_secret_value(),
        "X-Demo-Session": state["session"],
    }

    def request(path, method="GET", body=None, extra=None):
        req = Request(
            args.url.rstrip("/") + "/api/v1/" + path,
            method=method,
            headers=headers
            | ({"Content-Type": "application/json"} if body is not None else {})
            | (extra or {}),
            data=json.dumps(body).encode() if body is not None else None,
        )
        with urlopen(req, timeout=40) as response:
            return json.load(response)

    if args.phase == "before":
        request("demo/session", "POST", {})
        meeting = request(
            "meetings",
            "POST",
            {
                "title": "Runtime restart persistence proof",
                "occurred_at": "2026-10-06T00:00:00Z",
                "duration_ms": 10000,
                "segments": [
                    {
                        "speaker": "Sam",
                        "start_ms": 0,
                        "end_ms": 10000,
                        "text": "We decided to verify durable meeting storage.",
                    }
                ],
            },
            {"Idempotency-Key": str(uuid4())},
        )
        state["meeting"] = meeting["id"]
        base = "meetings/" + state["meeting"]
        request(
            base + "/action-items",
            "POST",
            {"text": "Manual task survives runtime restart", "due_date": "2026-10-20"},
        )
        request(
            base + "/summary",
            "PATCH",
            {"notes": "Persistent synthetic notes café 😀"},
            {"If-Match": "1"},
        )
        segment = request(base + "/transcript")["items"][0]
        annotation = {"segment_id": segment["public_id"], "segment_version": segment["version"]}
        request(base + "/comments", "POST", annotation | {"body": "Persistent comment"})
        request(
            base + "/highlights",
            "POST",
            annotation
            | {
                "start_offset": 0,
                "end_offset": 2,
                "selected_text": "We",
                "note": "Persistence highlight",
            },
        )
        request(
            base + "/soundbites",
            "POST",
            {"title": "Persistent soundbite", "start_ms": 0, "end_ms": 10000},
        )
    base = "meetings/" + state["meeting"]
    actual = {
        suffix: request(base + suffix)
        for suffix in [
            "",
            "/transcript",
            "/action-items",
            "/summary",
            "/comments",
            "/highlights",
            "/soundbites",
        ]
    }
    actual["search"] = request("search?q=durable")
    if not any(hit["meeting_id"] == state["meeting"] for hit in actual["search"]["items"]):
        raise SystemExit("Persistence verification failed: search lost the meeting.")
    if args.phase == "before":
        state["expected"] = actual
        with args.state.open("x") as output:
            args.state.chmod(0o600)
            json.dump(state, output)
        print("Saved meeting, task, notes, annotations, and search results for restart comparison.")
    else:
        if actual != state["expected"]:
            raise SystemExit("Persistence verification failed: saved records changed.")
        print("PASS: the same session retained identical records after restart.")


if __name__ == "__main__":
    main()
