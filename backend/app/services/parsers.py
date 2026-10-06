"""Bounded text parsers. Imported markup is never executable or rendered as HTML."""

import base64
import binascii
import json
import math
import re
import unicodedata
from html.parser import HTMLParser
from typing import Any

from pydantic import AwareDatetime, ConfigDict, Field, ValidationError

from app.core.errors import DomainError
from app.schemas.common import StrictModel
from app.schemas.imports import ImportRequest, ParsedTranscript
from app.schemas.meetings import MeetingCreate, PersonInput, SegmentInput


class JsonSegment(SegmentInput):
    model_config = ConfigDict(extra="forbid", strict=True)


class JsonPerson(PersonInput):
    model_config = ConfigDict(extra="forbid", strict=True)


class JsonDocument(StrictModel):
    schema_version: int = Field(1, strict=True, ge=1, le=1)
    title: str | None = Field(None, max_length=200)
    occurred_at: AwareDatetime | None = None
    duration_ms: int | None = Field(None, strict=True, ge=1000, le=21600000)
    participants: list[JsonPerson] = Field(default_factory=list, max_length=100)
    segments: list[JsonSegment] = Field(min_length=1, max_length=3000)


def invalid(message: str) -> DomainError:
    return DomainError(422, "invalid_transcript", message)


def decode(data: ImportRequest) -> str:
    if data.filename:
        if not re.fullmatch(r"[^./\\\x00-\x1f]+\.(txt|vtt|json)", data.filename, re.I):
            raise invalid(
                "Use a simple .txt, .vtt, or .json filename without paths or extra extensions."
            )
        if data.filename.rsplit(".", 1)[1].lower() != data.format:
            raise invalid("The filename extension must match the selected format.")
    try:
        raw = (
            base64.b64decode(data.content_base64, validate=True)
            if data.content_base64 is not None
            else (data.content or "").encode("utf-8")
        )
        if len(raw) > 2 * 1024 * 1024:
            raise DomainError(413, "too_large", "Transcript files must be 2 MiB or smaller.")
        text = raw.decode("utf-8-sig")
    except (UnicodeError, binascii.Error) as error:
        raise invalid("The file must contain valid UTF-8 text.") from error
    if not text.strip() or "\x00" in text or any(ord(c) < 32 and c not in "\t\r\n" for c in text):
        raise invalid("The transcript is empty or contains binary control characters.")
    if re.match(r"\s*<(?:!doctype|html|\?xml)", text, re.I):
        raise invalid("HTML and XML documents are not accepted.")
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def timestamp(value: str, milliseconds: bool = False) -> int:
    pattern = r"(?:(\d{2}):)?(\d{2}):(\d{2})" + (r"\.(\d{3})" if milliseconds else "")
    match = re.fullmatch(pattern, value)
    if not match:
        raise invalid(
            f"Invalid timestamp: {value[:30]}. Use HH:MM:SS" + (".mmm." if milliseconds else ".")
        )
    hours, minutes, seconds = [int(x or 0) for x in match.groups()[:3]]
    if minutes > 59 or seconds > 59 or hours > 6:
        raise invalid(f"Timestamp is outside supported bounds: {value[:30]}.")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + (int(match[4]) if milliseconds else 0)


def estimated_length(text: str) -> int:
    return max(1000, math.ceil(len(text.split()) * 60000 / 150))


def parse_txt(text: str) -> ParsedTranscript:
    timed = bool(re.search(r"^\[", text, re.M))
    turns: list[tuple[int | None, str, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = re.match(r"^\[([^]]+)\]\s*([^:]{1,120}):\s*(.*)$", line)
        person = re.match(r"^([^:\[\]]{1,120}):\s*(.*)$", line)
        if match:
            turns.append((timestamp(match[1]), match[2].strip(), match[3].strip()))
        elif line.startswith("["):
            raise invalid(f"Line {number}: expected [MM:SS] Speaker: text.")
        elif person:
            if timed:
                raise invalid(f"Line {number}: a speaker turn is missing its timestamp.")
            turns.append((None, person[1].strip(), person[2].strip()))
        elif turns:
            start, speaker, previous = turns[-1]
            turns[-1] = (start, speaker, previous + "\n" + line.strip())
        else:
            turns.append((None, "Unknown speaker", line.strip()))
    segments: list[SegmentInput] = []
    position = 0
    for index, (start, speaker, content) in enumerate(turns):
        if not content.strip():
            raise invalid(f"Turn {index + 1} has no text.")
        start = position if start is None else start
        next_start = turns[index + 1][0] if index + 1 < len(turns) else None
        if next_start is not None and next_start < start:
            raise invalid(f"Turn {index + 2} starts before the previous TXT turn.")
        end = (
            next_start
            if next_start is not None and next_start > start
            else start + estimated_length(content)
        )
        segments.append(SegmentInput(speaker=speaker, start_ms=start, end_ms=end, text=content))
        position = end
    warnings = [
        "End times are estimated from the next turn or 150 words/minute. R"
        "eview the timing before importing."
    ]
    if not timed:
        warnings = [
            "Estimated timing: 150 words/minute, at least one second per turn."
            " No audio was analyzed."
        ]
    if any(s.speaker == "Unknown speaker" for s in segments):
        warnings.append("Unlabelled text uses Unknown speaker. You can correct it after import.")
    return ParsedTranscript(
        segments=segments,
        duration_ms=max((s.end_ms for s in segments), default=0),
        estimated_timing=True,
        warnings=warnings,
    )


class PlainCue(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.voice = "Unknown speaker"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "v":
            raw = self.get_starttag_text() or ""
            voice = re.match(r"<v(?:\.[\w.-]+)?\s+([^>]+)>", raw)
            if voice:
                self.voice = voice[1].strip()
        if tag == "br":
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def parse_vtt(text: str) -> ParsedTranscript:
    blocks = re.split(r"\n[ \t]*\n", text.strip())
    if not re.fullmatch(r"WEBVTT(?:[ \t].*)?", blocks[0].splitlines()[0]):
        raise invalid("VTT must begin with WEBVTT followed by a blank line.")
    segments: list[SegmentInput] = []
    unknown = False
    for number, block in enumerate(blocks[1:], 1):
        lines = block.splitlines()
        if lines[0].split(" ")[0] in {"NOTE", "STYLE", "REGION"}:
            continue
        timing = 0 if "-->" in lines[0] else 1
        if timing >= len(lines):
            raise invalid(f"Cue {number}: missing timing line.")
        match = re.fullmatch(r"(\S+)\s+-->\s+(\S+)(?:[ \t]+.*)?", lines[timing])
        if not match:
            raise invalid(f"Cue {number}: malformed timing line.")
        cue = PlainCue()
        cue.feed("\n".join(lines[timing + 1 :]))
        content = "".join(cue.parts).strip()
        if not content:
            raise invalid(f"Cue {number}: empty text.")
        unknown = unknown or cue.voice == "Unknown speaker"
        segments.append(
            SegmentInput(
                speaker=cue.voice,
                start_ms=timestamp(match[1], True),
                end_ms=timestamp(match[2], True),
                text=content,
            )
        )
    if not segments:
        raise invalid("VTT contains no transcript cues.")
    return ParsedTranscript(
        segments=segments,
        duration_ms=max(s.end_ms for s in segments),
        warnings=[
            "Voice-less cues use Unknown speaker. NOTE, STYLE and REGION metadata are ignored."
        ]
        if unknown
        else [],
    )


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON fields")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON value")


def parse_json(text: str) -> ParsedTranscript:
    try:
        raw = json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
        pending: list[tuple[Any, int]] = [(raw, 0)]
        while pending:
            item, depth = pending.pop()
            if depth > 12:
                raise ValueError("JSON nesting exceeds 12 levels")
            if isinstance(item, dict):
                pending.extend((v, depth + 1) for v in item.values())
            elif isinstance(item, list):
                if len(item) > 3000:
                    raise ValueError("JSON array exceeds 3,000 entries")
                pending.extend((v, depth + 1) for v in item)
        document = JsonDocument.model_validate(raw)
        if "schema_version" not in raw:
            raise ValueError("schema_version: 1 is required")
    except (ValueError, RecursionError, ValidationError) as error:
        raise invalid(
            "Invalid JSON transcript. Use schema_version 1, valid typed fields"
            ", and bounded segments."
        ) from error
    return ParsedTranscript(
        title=document.title,
        occurred_at=document.occurred_at,
        participants=list(document.participants),
        segments=list(document.segments),
        duration_ms=document.duration_ms or max(s.end_ms for s in document.segments),
    )


def parse_validated(data: ImportRequest) -> ParsedTranscript:
    text = decode(data)
    parsed = {"txt": parse_txt, "vtt": parse_vtt, "json": parse_json}[data.format](text)
    # The create model is also authoritative for previews; acknowledgement is a separate UI choice.
    from datetime import UTC, datetime

    MeetingCreate(
        title=data.title or parsed.title or "Imported meeting",
        occurred_at=data.occurred_at or parsed.occurred_at or datetime.now(UTC),
        duration_ms=parsed.duration_ms,
        participants=data.participants if data.participants is not None else parsed.participants,
        segments=parsed.segments,
        tag_ids=data.tag_ids,
        estimated_timing=parsed.estimated_timing,
        acknowledge_estimated=True,
    )
    return parsed


def parse(data: ImportRequest) -> ParsedTranscript:
    try:
        return parse_validated(data)
    except ValidationError as error:
        raise invalid(
            "Transcript fields exceed supported limits or contain invalid timi"
            "ng. Check speakers, text, and duration."
        ) from error
