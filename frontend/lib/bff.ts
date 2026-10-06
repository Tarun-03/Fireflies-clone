import { NextRequest, NextResponse } from "next/server";
import { serverConfig } from "./server-config";
import { cookieName, csrf, equal, Session, verify } from "./session";

export class BrowserError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
export function failure(error: unknown) {
  const known = error instanceof BrowserError;
  return NextResponse.json(
    {
      error: {
        code: known ? error.code : "unavailable",
        message: known
          ? error.message
          : "The workspace is temporarily unavailable. Please retry.",
        field_errors: [],
        request_id: crypto.randomUUID(),
      },
    },
    {
      status: known ? error.status : 503,
      headers: { "Cache-Control": "no-store" },
    },
  );
}
export function sameOrigin(request: NextRequest, unsafe = false) {
  const { origin } = serverConfig();
  const site = request.headers.get("sec-fetch-site");
  const supplied = request.headers.get("origin");
  if (
    site === "cross-site" ||
    site === "same-site" ||
    (supplied && supplied !== origin) ||
    (unsafe && supplied !== origin) ||
    (!unsafe && site !== "same-origin" && supplied !== origin)
  )
    throw new BrowserError(
      403,
      "origin_rejected",
      "Open this workspace from its own application URL.",
    );
}
export function activeSession(request: NextRequest) {
  return verify(request.cookies.get(cookieName("session"))?.value, "session");
}
export function requireCsrf(request: NextRequest, session: Session) {
  sameOrigin(request, true);
  if (!equal(request.headers.get("x-csrf-token") ?? "", csrf(session)))
    throw new BrowserError(
      403,
      "csrf_rejected",
      "Your session token changed. Refresh and try again.",
    );
}
export async function boundedBody(
  request: Request,
  maximum = 3 * 1024 * 1024,
): Promise<Uint8Array> {
  const reader = request.body?.getReader();
  if (!reader) return new Uint8Array();
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const part = await reader.read();
      if (part.done) break;
      length += part.value.length;
      if (length > maximum) {
        await reader.cancel();
        throw new BrowserError(
          413,
          "too_large",
          "This file or request is too large.",
        );
      }
      chunks.push(part.value);
    }
  } finally {
    reader.releaseLock();
  }
  const result = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.length;
  }
  return result;
}
export async function backendFetch(
  path: string,
  sessionId: string,
  init: RequestInit = {},
) {
  const config = serverConfig();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${config.serviceToken}`);
  headers.set("X-Demo-Session", sessionId);
  return fetch(`${config.backend}/api/v1/${path}`, {
    ...init,
    headers,
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(40000),
  });
}
const uuid =
  "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
const routes: [RegExp, readonly string[]][] = [
  [/^me$/, ["GET"]],
  [new RegExp(`^meetings/${uuid}/segments/${uuid}/impact$`), ["GET"]],
  [/^me\/preferences$/, ["GET", "PATCH"]],
  [/^meetings$/, ["GET", "POST"]],
  [/^meetings\/import(?:\/preview)?$/, ["POST"]],
  [new RegExp(`^meetings/${uuid}$`), ["GET", "PATCH", "DELETE"]],
  [new RegExp(`^meetings/${uuid}/(?:tags|participants)$`), ["PUT"]],
  [
    new RegExp(
      `^meetings/${uuid}/(?:transcript|timeline|transcript/window|transcript/search|chapters|speakers|export)$`,
    ),
    ["GET"],
  ],
  [new RegExp(`^meetings/${uuid}/summary$`), ["GET", "PATCH"]],
  [new RegExp(`^meetings/${uuid}/summary/regenerate$`), ["POST"]],
  [
    new RegExp(
      `^meetings/${uuid}/(?:action-items|comments|highlights|soundbites)$`,
    ),
    ["GET", "POST"],
  ],
  [
    new RegExp(
      `^meetings/${uuid}/(?:action-items|comments|highlights|soundbites|segments|speakers)/${uuid}$`,
    ),
    ["PATCH", "DELETE"],
  ],
  [new RegExp(`^meetings/${uuid}/chat$`), ["GET", "POST", "DELETE"]],
  [/^(?:tags)$/, ["GET", "POST"]],
  [new RegExp(`^tags/${uuid}$`), ["PATCH", "DELETE"]],
  [/^(?:search|action-items|activity|participants)$/, ["GET"]],
  [new RegExp(`^(?:activity|participants)/${uuid}$`), ["PATCH"]],
];
export function allowedRoute(path: string, method: string) {
  return routes.some(
    ([pattern, methods]) => pattern.test(path) && methods.includes(method),
  );
}
