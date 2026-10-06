# Meeting workspace

An original, unofficial Fireflies-inspired meeting workspace using Next.js, FastAPI, and SQLite. Not affiliated with Fireflies. Use synthetic content only; anonymous workspaces are not production account authentication.

Framework dependencies are pinned in the npm and uv lockfiles: Next.js 16.3.8, FastAPI 0.142.2, SQLAlchemy 2.1.3, Alembic 1.20.0, and OpenAI Python 3.24.0.

## Local development

Requires Node.js 24 (tested with 24.5.0), npm 11, Python 3.13 (tested with 3.13.5), and uv 0.12.23. Install uv with `python3 -m pip install uv==0.12.23` in a tooling virtual environment if needed.

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env.local`. Generate two separate secrets using `python3 -c "import secrets; print(secrets.token_hex(32))"`. Set the same INTERNAL_API_TOKEN in both files and SESSION_SIGNING_SECRET only in the frontend file. Do not commit these files.

```sh
cd backend
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000 --no-access-log
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open [the local workspace](http://localhost:3000). Backend readiness is [available here](http://127.0.0.1:8000/health/ready).

## Checks

```sh
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

```sh
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

Docker Compose uses a named volume for the database. Set the environment files before running `docker compose up --build`. See the [deployment and operations guide](docs/deployment.md) for Render, Vercel, persistence checks, and current verification limits.

AI is disabled by default. No public repository or hosted application has been verified yet.

Database schema, seed behavior, backup and restore: [database guide](docs/database.md).

## Meeting library

The library supports title, attendee, tag, date, and duration filters; recent/oldest/title ordering; cursor pagination; and URL restoration. Tags, notifications, action-item completion, and theme/timezone/player preferences persist through the API.

![Meeting library](docs/screenshots/library-light-1440.png)

Run frontend unit tests with `npm test` and browser checks with `npm run test:e2e`. Browser checks use installed Google Chrome locally; CI uses Playwright Chromium. Both services must be running with `APP_ORIGIN=http://localhost:3000`.


## Notebook features

Create meetings from pasted transcripts, timed manual turns, TXT, VTT, or JSON. Edit metadata, attendees, speakers, and transcript turns with version-conflict recovery. Use synchronized playback, literal transcript search, source links, and timed chapters. Save personal notes and actionable tasks; regenerate grounded summaries while preserving edited, completed, and manual work.

Comments, Unicode range highlights, and named soundbites persist in SQLite. Global FTS search finds title/transcript evidence with speaker/time context. The meeting assistant saves questions and cited answers, with a working OpenAI adapter and a clearly labelled local extractive mode. TXT, Markdown, and PDF exports provide explicit numbered parts for long meetings.

![Meeting notebook](docs/screenshots/notebook-1440.png)

Read the [evaluation walkthrough](docs/evaluation.md), [architecture](docs/architecture.md), [API](docs/api.md), [import formats](docs/imports.md), [intelligence and exports](docs/intelligence.md), [design references](docs/design.md), and [security review](docs/security.md).

From the repository root, run `node scripts/audit_npm.mjs`, `backend/.venv/bin/pip-audit`, `python3 scripts/scan_secrets.py`, and `python3 scripts/check_client_secrets.py` after building. The npm gate retains one documented unpatched development-only glob advisory; runtime findings fail the check. GitHub Actions is configured to run the checks and browser suite without live AI credentials.
