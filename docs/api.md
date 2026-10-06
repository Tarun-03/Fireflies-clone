# API

The canonical contract is [openapi.json](openapi.json), generated from FastAPI response and request models. The frontend generates `lib/contracts.d.ts` with `npm run contracts`. Run `uv run python -m scripts.openapi` from the backend to refresh the source document.

Browser calls go through `/api/v1/` on the frontend. Its route allowlist injects service credentials and a session UUID from a verified cookie. Do not call backend business routes from browser code. Backend CLI tests require both `Authorization: Bearer <INTERNAL_API_TOKEN>` and `X-Demo-Session: <UUID>`; this trusted interface is for operators, not a login API.

## Browser session endpoints

`GET /api/session/csrf` checks same-origin fetch metadata, issues a signed ten-minute nonce cookie for a new visitor, and returns a CSRF token. It creates no workspace. `POST /api/session`, with exact Origin, JSON `{}`, and `X-CSRF-Token`, verifies the nonce or existing session and calls the internal session endpoint. It sets a signed thirty-day HttpOnly cookie and returns the session-bound mutation token. Production requires HTTPS and host-only `__Host-` cookies. Responses use no-store caching.

Business mutations require `X-CSRF-Token`; updates/deletes also require `If-Match` containing the resource version. Meeting creation requires an `Idempotency-Key` of 16–100 characters. Reusing a key with different content fails with 409. Keep drafts on conflicts and reload the current version before retrying.

Meeting lists use a bounded page size and a filter-bound keyset cursor. Supported sort values are recent, oldest, and title. `after` is inclusive UTC; `before` is exclusive UTC. The frontend must convert selected local calendar dates to timezone boundaries.

Response errors contain `error.code`, a safe `error.message`, bounded `field_errors`, and a `request_id`. Invalid inputs use 422, missing service/session credentials 401, out-of-scope IDs 404, missing versions 428, stale versions 409, excessive bodies 413, quotas/rates 429, and temporary database failures 503.

Additional routes support `/participants` for filter/owner choices, versioned participant-name corrections, meeting participant replacement with explicit unassign/reassign behavior, and meeting speaker-name correction. Workspace tasks are available at `/action-items`. These serve the library, task editor, and meeting metadata editor.
