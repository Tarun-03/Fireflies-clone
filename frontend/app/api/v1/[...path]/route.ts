import { NextRequest, NextResponse } from "next/server";
import {
  activeSession,
  allowedRoute,
  backendFetch,
  boundedBody,
  BrowserError,
  failure,
  requireCsrf,
  sameOrigin,
} from "@/lib/bff";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
async function handle(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  try {
    const path = (await context.params).path.join("/");
    if (!allowedRoute(path, request.method))
      throw new BrowserError(404, "not_found", "This action is unavailable.");
    const session = activeSession(request);
    if (!session)
      throw new BrowserError(
        401,
        "session_required",
        "Refresh to start your workspace.",
      );
    const unsafe = !["GET", "HEAD"].includes(request.method);
    if (unsafe) requireCsrf(request, session);
    else sameOrigin(request);
    const headers = new Headers();
    for (const name of [
      "content-type",
      "if-match",
      "idempotency-key",
      "x-transcript-revision",
    ])
      if (request.headers.has(name))
        headers.set(name, request.headers.get(name)!);
    const body = unsafe ? await boundedBody(request) : undefined;
    const response = await backendFetch(
      `${path}${request.nextUrl.search}`,
      session.id,
      {
        method: request.method,
        signal: request.signal,
        headers,
        body: body?.length ? Buffer.from(body) : undefined,
      },
    );
    const outgoing = new Headers({
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    });
    for (const name of [
      "content-type",
      "content-disposition",
      "x-request-id",
      "retry-after",
    ])
      if (response.headers.has(name))
        outgoing.set(name, response.headers.get(name)!);
    const result = new NextResponse(response.body, {
      status: response.status,
      headers: outgoing,
    });
    return result;
  } catch (error) {
    return failure(error);
  }
}
export {
  handle as GET,
  handle as POST,
  handle as PATCH,
  handle as PUT,
  handle as DELETE,
};
