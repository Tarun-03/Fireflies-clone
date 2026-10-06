# Deployment and operations

The application targets Vercel for `frontend/` and one Docker-based Render backend with a persistent disk. The checked-in Blueprint is configuration, not evidence of a live deployment. No public repository, hosted URL, or live OpenAI request has been verified yet.

## Local containers

Configure the two environment files as described in the README, then run from the repository root:

```sh
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open [the local app](http://localhost:3000). The backend waits for its named `/var/data` volume, drops container root privileges to UID 10001, applies Alembic migrations at runtime, validates the synthetic template, and starts one Uvicorn worker with eight synchronous request threads and bounded concurrency. The frontend starts only after backend readiness. The published ports bind to localhost. This local HTTP configuration intentionally uses development cookies; it is not the hosted production configuration.

`docker compose restart backend` retains the named volume. `docker compose down` retains it too. Do not use `down -v` unless intentionally deleting the entire local database. Both Docker build contexts exclude environment files and development databases. The backend image includes fixture and licensed PDF font assets; the frontend standalone image includes static assets and sample audio.

## Render backend

Use the root `render.yaml` Blueprint for a new authorized service. It sets Docker context `backend/`, Dockerfile `backend/Dockerfile`, one `starter` instance, a 1 GiB disk at `/var/data`, and `/health/ready`. Supply a strong INTERNAL_API_TOKEN and ALLOWED_HOSTS containing the service's actual public hostname plus `localhost,127.0.0.1`. Do not use a wildcard host. Keep DATABASE_URL exactly `sqlite:////var/data/meeting-workspace.db` and ENVIRONMENT=production.

Render persistent disks require paid compute. They are available only at runtime, on one instance, and do not support zero-downtime deployment. Consequently, migration runs in the container startup path after the disk mounts, never in a build or pre-deploy hook. A brief unavailable period during a backend deploy is expected. These constraints were checked against [Render's persistent-disk documentation](https://render.com/docs/disks). The Blueprint was validated against the current schema referenced by [Render's Blueprint specification](https://render.com/docs/blueprint-spec).

Creating the service/disk may incur charges. Use an existing authorized paid plan or obtain billing approval in the Render dashboard; no service has been purchased by this project. Check the current service and disk prices shown in that dashboard before provisioning. A free ephemeral filesystem is not a supported substitute.

## Vercel frontend

Import the intended public GitHub repository, set the project root to `frontend/`, and use the Next.js framework preset with Node.js 24. Build uses `npm ci` and `npm run build`; `vercel.json` includes those commands. Configure these as server-only production environment variables:

| Variable | Value |
| --- | --- |
| APP_ENV | `production` |
| APP_ORIGIN | The exact `https://` frontend origin, without a trailing slash |
| BACKEND_URL | The exact `https://` Render backend origin |
| INTERNAL_API_TOKEN | The same secret supplied to Render |
| SESSION_SIGNING_SECRET | A separate random secret of at least 32 characters |

Never use NEXT_PUBLIC names. Configure a stable production origin before evaluating sessions; preview domains require their own explicit origin and isolated backend configuration. The BFF will reject mismatched origins and cross-origin mutations. Production cookies are Secure, HttpOnly, host-only, and signed.

The provider deadline is 30 seconds, backend-fetch deadline 40 seconds, and BFF maxDuration 60 seconds. Requests are bounded to 3 MiB, JSON responses below 1 MiB, and export parts below 4 MiB. Current [Vercel function limits](https://vercel.com/docs/functions/limitations) specify a 4.5 MB request/response payload limit and a 300-second Hobby function maximum for the documented runtimes. The application stays below those limits without assuming streaming bypasses them. Actual hosted downloads and timeout behavior still require live verification.

## Optional OpenAI

Set only on Render: LLM_PROVIDER=openai, OPENAI_API_KEY, and an explicit LLM_MODEL that supports the Responses API with structured outputs and a context window of at least 128k tokens. Confirm the chosen model's current availability for your provider project before enabling it. The adapter sends at most 24,000 selected transcript characters for regeneration; chat uses 18,000 evidence characters plus bounded history/question. Structured outputs are capped at 4,000 tokens for summaries and 2,000 for chat. The context requirement leaves room for worst-case Unicode tokenization and JSON overhead.

The implementation uses the [official OpenAI Responses structured-output interface](https://developers.openai.com/api/docs/guides/structured-outputs), fixed `https://api.openai.com/v1`, no tools, no retries, and `store=false`. Users must choose OpenAI mode and consent before selected text is sent. Set provider-project spending limits. Verify with a synthetic meeting: choose OpenAI, ask a supported question, confirm provider provenance and source citations, then disable the key and confirm labelled fallback. No live request has been verified; deterministic adapter tests do not substitute for that check.

## Live acceptance procedure

1. Check both HTTPS origins and backend `/health/ready`. Confirm CSP, no-store API responses, anti-framing/content-type headers, and Secure HttpOnly host-only session cookies.
2. Run the [evaluation workflow](evaluation.md) through the deployed frontend, including imports, chat fallback, and every export format. Check actual payload sizes in the browser's network inspector.
3. In the same browser session, create a uniquely titled synthetic meeting and a manual task. Record their IDs and content privately. Restart or redeploy the backend through Render, then reload the same session and compare the exact records. A new seed is not persistence evidence.
4. Use a separate browser profile to confirm those IDs return 404 and a separate workspace is created. Verify CSRF/origin rejection and retained drafts after controlled errors.
5. Confirm the deployed Git commit matches the submitted repository revision and verify GitHub Actions before adding public URLs/status to the README.

## Backup, restore, and retention

Use the [SQLite backup/restore commands](database.md) from the running backend shell. Store backups outside the database volume using an operator-approved private destination. Backups contain workspace content and must not be published. Restore into a new file while the service is stopped, check integrity/foreign keys, then switch to the restored file. Do not copy a live `.db` without its WAL, and do not treat filesystem snapshots as a replacement for consistent database backup.

Cleanup defaults to dry-run. Expired-workspace deletion requires both `--apply` and `--expired-workspaces`; a seven-day grace period follows session expiry. Monitor disk usage and quota responses. Rotate secrets using the procedure in [security.md](security.md).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Startup rejects the database path | Confirm the persistent disk is mounted at `/var/data` and writable by UID 10001. Startup changes directory ownership before dropping privileges; existing files from another UID need an operator correction. |
| Readiness returns 503 | Check runtime migration output, migration-head match, FTS5 support, disk space, and the fixed SQLite path. Do not reset the database. |
| Browser says unavailable | Compare INTERNAL_API_TOKEN across both servers and check backend HTTPS/ALLOWED_HOSTS. |
| Origin or CSRF rejected | Use APP_ORIGIN exactly; refresh for a fresh token. Do not weaken the origin check. |
| Session expired | Start a new session. Old content is retained for explicit operator cleanup; there is no account recovery in this demo. |
| Busy database | Keep one backend instance/worker, check long-running operations, and retry after the controlled 503. Provider calls release the writer lock. |
| AI unavailable | Check provider/key/model, spending controls, and cooldown. Extractive mode remains functional. |
| Long export has multiple parts | Download every numbered part. TXT/Markdown preserve characters unsupported by the PDF font. |


## Recorded verification

The runtime startup command was executed locally against the existing database. Its migrations and fixture validation completed, readiness returned 200, and the same-session meeting, manual task, transcript, and personal notes matched their pre-restart values exactly. Startup tests also verify repeatable empty-database migration without creating visitor workspaces and readiness rejection of an outdated schema.

Compose configuration parsing and the current Render JSON schema validation passed. Docker Desktop is installed, but the engine socket remained unavailable after its CLI launch attempt; local image builds/container restart checks have therefore not completed. The container CI job builds both images, starts the named volume, and runs the repeatable backend probe before and after restart. It still needs an actual CI execution after publication.

The probe can be repeated from `backend/` against a local service:

```sh
uv run python -m scripts.persistence_probe before --state /private/tmp/new-persistence-proof.json
# Restart the backend while retaining its database/volume.
uv run python -m scripts.persistence_probe after --state /private/tmp/new-persistence-proof.json
```

The state file is private and contains a session ID; do not publish it. This probe verifies backend records. The separate live acceptance procedure is still required for production browser cookies, deployed BFF limits, HTTPS headers, and hosting redeploy persistence.

`backend/production.env.example` and `frontend/production.env.example` provide fixed production examples using reserved example domains and empty secret values. Copy their settings into the respective hosting dashboards; do not deploy them without replacing the origins/hosts and supplying distinct real secrets.
