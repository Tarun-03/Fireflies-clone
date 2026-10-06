# Evaluation guide

Use synthetic data only. Start both services using the README and open the frontend. A fresh browser profile receives eight private sample meetings; an incognito profile gets a different workspace. The local implementation uses the real API and SQLite for all records.

## A complete walkthrough

1. Filter the library by title, attendee, tag, date, and duration. Refresh and use Back to verify URL state. Change sort order and clear filters.
2. Open Engineering standup. Play the labelled sample tones, pause, change speed, seek a timestamp, search for “review,” and select a hit. Scroll manually to suspend follow. The original sample tones are not the meeting recording.
3. Create a meeting by pasting `Sam: I will verify the café launch.` and `Lee: We decided to run the pilot.` Preview, acknowledge estimated timing, and create. The Upload tab also accepts the downloadable TXT, VTT, and JSON examples; Manual entry accepts timed turns.
4. Edit a turn and notice the stale summary. Regenerate in Extractive mode. Add a manual task with an owner/date, complete it, edit personal notes, regenerate again, and confirm personal work remains.
5. Use Annotate turn to add a comment or select a Unicode-safe range. Reopen it from the tools rail, edit its note, and jump to the source. Save a soundbite, play its bounded interval, and export its timestamped excerpt.
6. Press Ctrl/Cmd+K and search a distinctive phrase from your imported meeting. Open the result and confirm the matching turn is selected. Filter global results by participant, tag, kind, and UTC date.
7. Open Meeting assistant, ask about the pilot, and follow a citation. Refresh to verify history persistence. Ask an unrelated question to see the unsupported-evidence response. Extractive mode returns exact excerpts and does not contact a model.
8. Export the complete notebook as TXT, Markdown, and PDF. Toggle timestamps/speakers and choose summary/transcript/tasks. Download every numbered part for a large meeting.
9. Open Settings, change light/dark/system and timezone/speed preferences, save, and refresh. Review the notebook at phone and desktop widths. Navigation, dialogs, and player controls support keyboard input.
10. Delete your imported meeting with confirmation. Refresh and search again; its records and hits should be absent. Existing synthetic meetings are not reseeded after deletion.

## Repeatable checks

The browser suite covers the complete walkthrough, five creation paths, optimistic conflicts with retained drafts, failed mutation recovery, two-session read/delete/export/chat isolation, 3,000-turn seeking, annotation Unicode offsets, all download formats, theme persistence, and sixteen library/notebook breakpoint/theme views. Tests use an installed Chrome locally and Playwright Chromium on CI. Keep both servers running before `npm run test:e2e`.

Backend tests migrate temporary SQLite databases. They exercise composite foreign keys, FTS rollback/rebuild, backup/restore, imports and payload limits, ownership/version checks, idempotency, source invalidation, response budgets, quotas, dry-run maintenance, mocked provider success/failures, cancellation, and changes during generation. Provider mocks exist only in tests.

Local process-restart persistence was demonstrated with an imported meeting, transcript, task, and personal notes under the same session. Backup/restore integrity and foreign-key checks also passed. Hosting redeploy persistence remains unverified until deployment credentials and a persistent service are available. CI is configured, but a remote CI run is not claimed until the repository is published.

## Intentional boundaries

Real authentication, live recording/transcription, integrations, and team sharing are explicit Coming soon views. Imported meetings use labelled simulated playback. Soundbites export text excerpts, not audio clips. Anonymous cookies expire after thirty days; losing the cookie loses normal access to that workspace. PDF supports the bundled font’s characters, with explicit Unicode-code fallback elsewhere; TXT and Markdown retain original text. Optional OpenAI calls require explicit consent and backend configuration; no live call has been verified.

Local validation on October 6, 2026: 79 backend tests, 10 frontend unit tests, and 9 Playwright workflows passed. Ruff, strict mypy, ESLint, TypeScript, formatting, the Webpack production build, a fresh locked production Python install/import, and Alembic schema-drift checking passed. Axe reported no serious/critical findings in the tested views. The runtime npm audit and Python dependency audit returned no known findings; the documented development-only glob exception remains.
