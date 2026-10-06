import { NextRequest, NextResponse } from "next/server";
import { activeSession, failure, sameOrigin } from "@/lib/bff";
import { cookieName, cookieOptions, csrf, issue } from "@/lib/session";
export async function GET(request: NextRequest) {
  try {
    sameOrigin(request);
    const session = activeSession(request);
    const issued = session ? null : issue("nonce");
    const payload = session ?? issued?.payload;
    if (!payload) throw new Error("Missing token payload");
    const response = NextResponse.json(
      { csrf_token: csrf(payload), ready: !!session },
      { headers: { "Cache-Control": "no-store" } },
    );
    if (issued)
      response.cookies.set(
        cookieName("nonce"),
        issued.value,
        cookieOptions(issued.seconds),
      );
    return response;
  } catch (error) {
    return failure(error);
  }
}
