import { NextRequest, NextResponse } from "next/server";
import {
  activeSession,
  backendFetch,
  boundedBody,
  BrowserError,
  failure,
  requireCsrf,
} from "@/lib/bff";
import { cookieName, cookieOptions, csrf, issue, verify } from "@/lib/session";
export async function POST(request: NextRequest) {
  try {
    const current = activeSession(request);
    const nonce = verify(
      request.cookies.get(cookieName("nonce"))?.value,
      "nonce",
    );
    const prior = current ?? nonce;
    if (!prior)
      throw new BrowserError(
        403,
        "csrf_required",
        "Refresh the page to start your workspace.",
      );
    requireCsrf(request, prior);
    if (request.headers.get("content-type") !== "application/json")
      throw new BrowserError(
        415,
        "invalid_type",
        "A JSON request is required.",
      );
    const body = await boundedBody(request, 1024);
    if (new TextDecoder().decode(body).trim() !== "{}")
      throw new BrowserError(
        422,
        "invalid_input",
        "The session request must be empty.",
      );
    const created = current ? null : issue("session");
    const session = current ?? created?.payload;
    if (!session) throw new Error("Missing session");
    const backend = await backendFetch("demo/session", session.id, {
      method: "POST",
    });
    if (!backend.ok)
      return new NextResponse(await backend.text(), {
        status: backend.status,
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-store",
        },
      });
    const response = NextResponse.json(
      { ready: true, csrf_token: csrf(session) },
      { headers: { "Cache-Control": "no-store" } },
    );
    if (created)
      response.cookies.set(
        cookieName("session"),
        created.value,
        cookieOptions(created.seconds),
      );
    response.cookies.set(cookieName("nonce"), "", cookieOptions(0));
    return response;
  } catch (error) {
    return failure(error);
  }
}
