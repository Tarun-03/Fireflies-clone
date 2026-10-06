# Transcript imports

Create meeting supports pasted text, one UTF-8 `.txt`, `.vtt`, or `.json` file, and manually entered timed turns. Download examples from the upload dialog or `frontend/public/examples/`.

Files are limited to 2 MiB; the complete request is limited to 3 MiB at both services. Files travel as bounded base64 inside a JSON request, never as a disk path or public upload. A submitted filename must be a simple name with one supported extension. File content must decode as UTF-8; binary controls, NUL, HTML/XML documents, invalid parser input, and unknown JSON fields are rejected. Preview returns at most ten turns. Creation parses and validates the original content again and writes all related records in one transaction.

TXT accepts `[MM:SS] Speaker: text` or `[HH:MM:SS] Speaker: text`, followed by optional continuation lines. Untimed speaker text is also accepted. TXT estimates end times from the next turn or 150 words per minute, with at least one second for an estimated turn; import requires explicit acknowledgement. Unlabelled text uses `Unknown speaker`. Mixed timed and untimed speaker turns are rejected.

VTT accepts WEBVTT, optional cue IDs, millisecond timestamps, multiline cues, voice tags, and overlapping intervals. Cue markup becomes literal plain text. NOTE, STYLE, and REGION blocks are ignored; no styling, script, or remote content is applied. Cues without voices use `Unknown speaker` with a warning.

JSON requires `schema_version: 1` and a nonempty `segments` array of `{speaker, start_ms, end_ms, text}`. Optional fields are `title`, `occurred_at` (timezone-aware ISO timestamp), `duration_ms`, and `participants` (`display_name`, optional `email`). Imported summaries and tasks are not accepted. Numeric times must be integers. Duplicate properties, non-finite numbers, nesting beyond 12 levels, and arrays beyond 3,000 items are rejected. The meeting date and attendees are visible and editable before creation.

All formats enforce 3,000 turns, 100 speakers/attendees, 10,000 characters per turn, two MiB of transcript text, and six-hour duration. Overlap is valid; explicit duration must contain every turn. Creation produces source-linked extractive notes, conservative commitment tasks, and timed outline entries. Repeating the same request key and content replays the original result.

Edits require the last resource version. A conflict retains the user's draft and offers an explicit latest-version reload. Text edits remove acknowledged affected highlights and detach live chat citations while preserving historical quoted evidence. Deletion removes attached comments/highlights and clears generated source references. All transcript edits increment the meeting revision, marking generated notes stale.

Local verification on 2026-10-06 covered all five creation flows in Chromium, transcript editing after reload, stale-version draft recovery, and deletion. A separate API comparison confirmed that the same session retained identical imported meeting metadata, transcript, action items, and notes after stopping and restarting the local Uvicorn process with the existing SQLite database. This is local persistence evidence, not a hosted redeployment claim.
