# Security and data handling

This is an anonymous demonstration for synthetic meeting data. No security audit or penetration test is claimed. An anonymous workspace is not a verified identity. Losing its session cookie prevents normal access to its existing data.

Configuration requires a service token of at least 32 characters. Example files contain no working secrets. Local environment files and database/WAL files are excluded from Git. SQLite connections use foreign keys, WAL, full synchronous durability, and a bounded busy timeout.

## Dependency review

Checked October 6, 2026. Next.js 16.3.8 includes the September security updates. The runtime npm dependency audit returned no findings during initial installation.

The full npm audit reports five high-severity dependency-chain entries originating from one unpatched development-only advisory: [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm), braces <=3.0.3. It is reached through Next.js's lint plugin → fast-glob → micromatch. npm and the advisory list no patched braces release. The application does not accept glob patterns from users; lint operates on checked-in source with fixed patterns, and the production standalone image excludes development tooling. This is a narrowly scoped tooling exception, not a suppressed runtime finding. Recheck when upgrading tooling; arbitrary untrusted glob patterns must never be passed to this dependency.

ESLint 10 uses the official @eslint/compat adapter for the Next.js React/import/accessibility rules that still declare ESLint 9 peer ranges. No rules are disabled.


## Tested application boundaries

Backend tests use migrated temporary SQLite databases. They cover service authentication, two-session read/write/delete isolation, nested task/speaker substitution, unknown fields, missing/stale versions, idempotent create and conflicting replays, streamed body limits, invalid dates, and the global workspace quota. Database tests cover foreign keys, temporal constraints, Unicode highlight consistency, rollback/index rebuild, and chat citation preservation after deletion.

The browser proxy forwards only content-type, version, idempotency, and transcript-revision request headers. Incoming Authorization and workspace headers are never forwarded. Backend targets come only from server configuration; redirects are rejected. GET and mutation handlers validate same-origin browser metadata, and mutations additionally require exact Origin and session-bound CSRF. Production configuration uses distinct server secrets, HTTPS, Secure host-only cookies, CSP nonces, anti-framing and content-type headers. Styles allow inline CSS for framework/UI layout; scripts do not allow unsafe-inline or production unsafe-eval.

Single-process backend rate limits enforce reads, writes, and global bootstrap limits; no Vercel process-local rate map is used. Global quota and meeting/segment/text checks run inside the reserved write transaction, and local SQLite free space retains a reserve; remote mode never checks Render disk space. No arbitrary forwarded client IP is trusted.

## Hardening and current verification

The October 6 recheck found no known Python dependency vulnerabilities and no npm runtime findings. The same single unpatched development glob advisory remains; `scripts/audit_npm.mjs` permits only its named chain and fails on any other finding or any runtime advisory. `scripts/scan_secrets.py` scans tracked working files and all Git-history blobs for common provider/token/private-key patterns without printing matched values. `scripts/check_client_secrets.py` compares configured server secrets against built browser JavaScript. Both local scans passed. Pattern scans cannot detect every possible secret.

The BFF rejects oversized streamed bodies without Content-Length, strips caller-supplied service/session headers, validates exact origin and CSRF, and bounds downstream JSON and downloads. Browser tests exercise actual two-session isolation and failed mutation recovery. SQL/FTS inputs are bound and FTS operators are escaped into literal terms. Import and PDF text never becomes executable markup. OpenAI uses a fixed HTTPS endpoint with no model tools; malformed or foreign citations fall back to explicitly labelled excerpts.

Default rate limits are 120 reads/minute, 30 writes/minute, 5 creates/imports per ten minutes, 10 exports/minute, and 5 generation requests/minute per session. Read/write/import/export/AI settings are configurable. The global allowance is twenty new workspaces per minute, 500 workspaces, and a 512 MiB logical transcript budget. Local mode additionally checks live SQLite-page allocation. Reopening a verified session does not consume the new-workspace counter. Global protection is used because this deployment does not configure a reliable client-IP trust chain; arbitrary forwarded IP headers are ignored.

Individual workspaces allow 100 meetings, 100,000 turns, a conservative 100 MiB transcript allowance, 500 participant identities, and 100 tags. Meetings allow 500 combined annotations, including at most 100 soundbites, 100 tasks, and fifty saved chat exchanges. These stricter finite bounds keep responses and ancillary storage predictable. In local mode, writes except deletes check free-disk reserve and physical database quota so deletion can recover capacity. Remote mode keeps application quotas and delegates physical storage to Turso. Operator cleanup is dry-run by default and requires explicit flags for expired-workspace removal.

Three consecutive provider failures cause a sixty-second cooldown. The two global generation leases, bounded evidence/output, fixed deadlines, and per-session limits constrain cost but are not a billing guarantee; set a provider-project spending limit before enabling a public AI demo. The model may make incorrect claims despite valid citations. No live AI or hosted security behavior has been verified.

Application logs contain route templates, method, status, duration, and request ID. Run Uvicorn with `--no-access-log` so URLs containing search terms do not appear in default access logs. Avoid enabling verbose HTTP/SDK logging.

## Secret rotation

Generate distinct random values of at least 32 characters. Rotate INTERNAL_API_TOKEN on backend and frontend together; requests fail closed while mismatched. Rotate SESSION_SIGNING_SECRET on the frontend to invalidate existing browser cookies; old workspace records remain for operator retention handling. Rotate OPENAI_API_KEY only on the backend, revoke the old key in the provider console, and verify a synthetic request. Do not place secrets in NEXT_PUBLIC variables, screenshots, logs, source control, or issue descriptions.

TURSO_DATABASE_URL and TURSO_AUTH_TOKEN stay backend-only. Remote endpoints must be libsql:// Turso hostnames and are contacted over HTTPS. The token is passed separately, not embedded in the SQLAlchemy URL. Driver exceptions and configuration errors hide connection details. Rotate the database token in Turso and Render, then revoke the old token after a successful check. Secret/bundle scans include TURSO_AUTH_TOKEN. The backend never automatically falls back to an ephemeral local file when remote configuration is missing or invalid.
