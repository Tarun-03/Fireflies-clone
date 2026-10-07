# Free deployment: Vercel + Render + Turso libSQL

The frontend targets **Vercel Hobby**, the FastAPI container **Render Free**, and durable data **Turso Free, libSQL engine**. No paid disk is required. Local development still uses standard SQLite. The backend Compose service targets Linux amd64 to use the pinned libSQL wheel, including on Apple Silicon hosts. This configuration has not yet been deployed to the user's accounts; follow the verification gates below before calling it a verified hosted deployment.

## Database choice and evidence

The pinned client is `libsql==0.1.11`, Turso's libSQL client, using remote-only HTTPS in deployment. It does not use `pyturso`, `turso_serverless`, the rewritten Turso engine, PostgreSQL, or an embedded replica on Render. The published `sqlalchemy-libsql==0.2.0` still imports `libsql-experimental`; it was evaluated and not selected. Our small SQLAlchemy bridge uses SQLAlchemy's SQLite dialect, disables unsupported Python UDF registration, and maps libSQL's ValueError SQL failures into sanitized DBAPI errors. It preserves qmark parameters, commits, rollbacks, savepoints, foreign keys and existing SQL.

`pytest --libsql` executes the database/API tests against the actual local libSQL engine bundled with that same client, not a mock or a renamed SQLite connection. The standard pytest run remains on Python SQLite. Tests cover migrations up/down/drift, composite foreign keys, checks and cascade/cleanup triggers, BEGIN IMMEDIATE, rollback/savepoints, FTS5 MATCH/bm25 queries, index update/rollback/rebuild, imports, annotations, exports and scoped API behavior. A fresh-process test compares the same meeting/task/comment IDs and FTS results after closing the engine. These tests establish local engine compatibility, **not remote transport or hosted durability**.

Remote credentials are still needed to run `scripts.verify_database` and the hosted restart/redeploy probe. Docker execution is also unverified while the local engine is unavailable. CI runs both SQLite and libSQL suites; a successful remote CI run is not claimed.

Sources checked October 7, 2026: [Turso Python drivers](https://docs.turso.tech/sdk/python/quickstart), [official dialect source](https://github.com/tursodatabase/sqlalchemy-libsql), [Turso pragma limitations](https://docs.turso.tech/cloud/limitations).

## 1. Turso dashboard

1. Sign in to [Turso](https://app.turso.tech). Use a **Free** organization; do not select a paid upgrade.
2. Open **Databases**, choose **Create Database**, and name it `meeting-workspace`. Select **libSQL** if the engine selector is shown. Do not select the newer Turso engine. Use a primary region near the Render service (the Blueprint uses Singapore).
3. Open the database overview. Confirm it is a libSQL database and copy its `libsql://...turso.io` URL. A `turso://` URL is not accepted by this project. If the dashboard doesn't identify the engine, confirm it before proceeding. The documented CLI fallback is `turso db create meeting-workspace` **without `--tursodb`**.
4. Use the database's **Generate Token** control to create a read/write database token. Use a database token, not an organization management API token. Note its expiration and rotate it before expiry.
5. Save URL and token privately as `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`. They go only into the backend environment, never Vercel or any `NEXT_PUBLIC_*` variable.
6. Use an empty database for a new workspace deployment. Existing local data is not automatically uploaded. To carry it over, use the backup/import procedure below before pointing the backend at Turso.

For the optional CLI credential retrieval, use `turso db show --url meeting-workspace` and `turso db tokens create meeting-workspace` in a private terminal. Do not paste the token into chat, commits or logs.

## 2. Render dashboard

Push the committed project to the Git repository you intend to deploy. No push or service purchase is performed by the application.

1. Open [Render](https://dashboard.render.com), select **New → Blueprint**, and connect that repository.
2. Select the committed branch and the root **Blueprint Path** `render.yaml`. Review the proposed service: Docker, `plan: free`, one instance, no disk. Do not create a Render database or persistent disk.
3. Enter the prompted secrets/settings:

| Render variable | Value |
| --- | --- |
| `ENVIRONMENT` | `production` (Blueprint supplies this) |
| `TURSO_DATABASE_URL` | Your exact `libsql://...turso.io` database URL |
| `TURSO_AUTH_TOKEN` | Your private read/write database token |
| `INTERNAL_API_TOKEN` | Keep the existing internal token; use the same value on Vercel |
| `ALLOWED_HOSTS` | Actual Render hostname without scheme, followed by `,localhost,127.0.0.1` |
| `LLM_PROVIDER` | `disabled` (Blueprint supplies this) |
| `MAX_WORKSPACES` | `500` |
| `GLOBAL_TEXT_BYTES` | `536870912` |

4. If Render only assigns the final hostname after creation, use `localhost,127.0.0.1` initially, then immediately update **Environment → ALLOWED_HOSTS** to include the assigned hostname and redeploy. Do not use `*`.
5. Apply the Blueprint. The Dockerfile runs as UID 10001, executes `python -m scripts.start`, migrates the configured remote database, validates fixtures, and starts one Uvicorn worker. There is no separate paid pre-deploy command.
6. Open the service's **Events/Logs**. Successful startup reports database readiness. Then open `https://YOUR-SERVICE.onrender.com/health/ready`; expect `{"status":"ok"}`. Readiness checks migration head, foreign-key enforcement, and an actual FTS MATCH query.
7. In **Settings**, confirm **Instance Type: Free**, health path `/health/ready`, Docker context `./backend`, Dockerfile `./backend/Dockerfile`, and no disk. Leave the Docker command as defined by the image.

For an existing Blueprint-managed service, update the same Blueprint instead of creating a duplicate. If an old persistent disk contains needed data, back it up and verify its Turso import **before** detaching it; changing plans is not a data migration.

Source: [Render Blueprint setup](https://render.com/docs/infrastructure-as-code).

## 3. Vercel dashboard

1. Sign in to [Vercel](https://vercel.com), use your **Hobby** scope, and select **Add New → Project**. Import the same Git repository.
2. Set **Root Directory** to `frontend`, **Framework Preset** to Next.js, and **Node.js Version** to 24.x. Keep `npm ci` as Install Command and `npm run build` as Build Command. Leave Output Directory at its framework default.
3. Choose a stable project name. In **Environment Variables**, set these for **Production**:

| Vercel variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `APP_ORIGIN` | Exact frontend HTTPS origin, e.g. `https://YOUR-PROJECT.vercel.app`, no trailing slash |
| `BACKEND_URL` | Exact Render HTTPS origin, no trailing slash |
| `INTERNAL_API_TOKEN` | The existing matching Render token |
| `SESSION_SIGNING_SECRET` | The existing separate frontend signing secret |

4. Deploy. If the assigned domain differs from the planned origin, use **Project → Settings → Environment Variables** to correct `APP_ORIGIN`, then **Deployments → … → Redeploy**. Open the stable production domain, not the deployment-specific preview URL.
5. Keep `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, and provider keys off Vercel. Preview deployments need separately configured origins and an isolated backend; don't loosen origin/CSRF checks to make arbitrary previews work.
6. Test two browser sessions. Cookies remain Secure, HttpOnly, host-only, signed, and checked with CSRF/origin controls. Keep the signing secret unchanged during redeployment so existing visitors retain access to their saved workspace.

Sources: [Vercel environment variables](https://vercel.com/docs/environment-variables), [Hobby plan](https://vercel.com/docs/plans/hobby).

## 4. Verify the actual remote deployment

On your computer, in `backend/`, put the same Render database URL/token and internal service token into the ignored `.env`. Keep `ENVIRONMENT=development` when running diagnostics locally. Both Turso variables select remote mode; clearing both returns to local SQLite. The token is never a command-line argument.

```sh
uv sync --frozen
uv run alembic upgrade head
uv run alembic check
uv run python -m scripts.verify_database --require-remote
```

The compatibility probe creates a temporary synthetic workspace in a transaction, exercises actual application FTS triggers, scoped search, comments, tasks, foreign-key rejection and savepoints, then rolls everything back. It verifies absence through a fresh connection. Run it only with a token authorized for this database. Stop and investigate if it fails; do not substitute a different engine.

Wait for Render readiness, then from `backend/`:

```sh
uv run python -m scripts.persistence_probe before --url https://YOUR-SERVICE.onrender.com --state /tmp/meeting-hosted-proof.json
```

The probe creates synthetic records and stores a private session ID plus exact expected data in a new mode-0600 file. Keep that file; it is not a public test artifact.

1. In Render, use the service's **Manual Deploy → Restart service** control, then wait for readiness. If that control is absent, a new deployment also restarts the process, but record it as a redeployment rather than a separately verified restart.
2. Run:

```sh
uv run python -m scripts.persistence_probe after --url https://YOUR-SERVICE.onrender.com --state /tmp/meeting-hosted-proof.json
```

3. Next use **Manual Deploy → Deploy latest commit**; after readiness, run the identical `after` command again. Do not run `before` again: a new seed is not persistence proof.
4. Separately, in the same Vercel browser session create a meeting, task, comment, highlight and soundbite. Search a distinctive transcript phrase. Repeat restart/redeploy and verify the same IDs, text and search result remain. Test imports and every export format through Vercel, plus isolation in Incognito.

The backend probe compares meeting, transcript, tasks, notes, comments, highlights, soundbites and search results. Record deployment commit and timestamps only after these commands actually pass. Local engine reopen tests are not a replacement for this gate.

## Backup and restore

For **local SQLite**, continue using `scripts.storage backup/restore` as described in [database.md](database.md). Those file commands intentionally refuse remote mode instead of accidentally backing up an unrelated local file.

For **Turso**, use its database backup/point-in-time restore controls to create a **new database**, then verify it before changing the backend URL/token. Free-plan retention is short; keep private operator backups as well. Do not back up Render's ephemeral filesystem: it contains no production database.

The CLI command `turso db export meeting-workspace --output-file /PRIVATE/PATH/snapshot.db` exports a generation snapshot which **may lag recent writes**. It is not sufficient alone for an up-to-date backup. The official export documentation requires SDK synchronization. A fresh SDK replica can also be synchronized directly; run the following from `backend/` on a trusted operator computer, with a new private destination outside the repository:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import libsql
from app.core.config import get_settings
from scripts.storage import backup

settings = get_settings()
assert settings.remote_database
with TemporaryDirectory() as folder:
    replica = Path(folder) / "replica.db"
    connection = libsql.connect(
        str(replica),
        sync_url=settings.turso_database_url,
        auth_token=settings.turso_auth_token.get_secret_value(),
    )
    try:
        connection.sync()
    finally:
        connection.close()
    backup(replica, Path("/PRIVATE/PATH/new-backup.db"))
```

This uses a temporary replica only on the operator machine, never in the Render runtime. SQLite's backup API then creates a consistent copy and checks integrity and foreign keys. The remote sync path needs verification with real Turso credentials; it has not been claimed tested here. To obtain a fixed recovery point, stop application writes while taking and validating the backup.

To restore/migrate local data, create a **new libSQL database** with `turso db create meeting-workspace-restored --from-file /PRIVATE/PATH/new-backup.db` (no `--tursodb`), retrieve its credentials, run migrations/checks and the compatibility probe, then point Render at that URL/token and redeploy. Verify existing records and FTS before retiring the original. Never publish backups; they contain session IDs and all workspace content. Preserve the frontend signing secret and existing browser cookies if you want those anonymous sessions to continue working.

Sources: [Turso export caveat](https://docs.turso.tech/cli/db/export), [create/import database](https://docs.turso.tech/cli/db/create), [Python replica reference](https://docs.turso.tech/sdk/python/reference).

## Free-plan behavior and limits

Render Free sleeps after 15 idle minutes and can take about a minute to wake. The application's existing 40-second backend deadline can expire on the first request; wait for backend readiness and retry. Don't automatically replay a mutation with a new idempotency key. No paid keep-alive service is configured. Render's filesystem is disposable; Turso is the durable store. Render grants 750 shared free instance hours per month and can suspend service on exhausted allowances. Review Billing and spending controls; no upgrade is authorized by this guide. [Render Free limits](https://render.com/docs/free).

Turso currently lists 5 GB storage, 500 million monthly rows read, 10 million monthly rows written and one day of point-in-time recovery on Free. Check the organization's Usage page; this application does not implement Turso's billing meter. Reads from search/quotas and per-visitor synthetic seeding consume allowances. Local free-disk/page-allocation guards do not apply remotely; global transcript-byte, workspace, meeting, turn and annotation limits remain enforced in write transactions. [Turso pricing](https://turso.tech/pricing).

Vercel Hobby is intended for personal, non-commercial use. Keep the free deployment within that scope and its current allowances. Extractive summaries/chat work with `LLM_PROVIDER=disabled`; the optional LLM adapter remains in the code but no paid provider calls are enabled. [Vercel Hobby](https://vercel.com/docs/plans/hobby).

## Troubleshooting

- Startup requires Turso configuration: supply both database URL and token; production refuses local-file fallback.
- Readiness 503: check token expiry, libSQL engine selection, network access, migrations, foreign keys and FTS. Don't delete or reset the database.
- First browser request fails after idle: wake Render via readiness, wait, then retry.
- Browser unavailable: compare internal tokens and fixed HTTPS origins; don't expose secrets in client variables.
- Origin/CSRF rejection: use the exact production APP_ORIGIN, refresh, and keep the security checks enabled.
- Database busy/network failure: retry after the controlled error. Keep one backend worker/instance. A disconnected connection is discarded, and mutations are not automatically retried.

## Recorded local checks — October 7, 2026

92 tests passed on standard SQLite and the same 92 passed with `--libsql`. Ruff, formatting and strict mypy passed. Nine existing Playwright workflows passed against the updated local backend. The expanded backend probe passed across an actual local server restart, comparing the same session's meeting, task, transcript, notes, comments, highlights, soundbites and search results. Compose parsed successfully, locked dependency installation succeeded, and secret/history/browser-asset scans passed.

These are local results. Remote Turso HTTP transport, token authorization, real cloud migration/backup, Render restart/redeploy durability, Vercel hosting and container execution remain unverified pending credentials and a working Docker engine. No service was purchased or provisioned.
