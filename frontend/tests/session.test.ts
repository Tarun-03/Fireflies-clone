import { beforeEach, describe, expect, it, vi } from "vitest";
import { csrf, issue, verify } from "@/lib/session";
import { allowedRoute, requireCsrf, sameOrigin } from "@/lib/bff";
import { NextRequest } from "next/server";
beforeEach(() => {
  vi.stubEnv("INTERNAL_API_TOKEN", "test-service-token-at-least-32-characters");
  vi.stubEnv(
    "SESSION_SIGNING_SECRET",
    "different-test-signing-secret-with-32-characters",
  );
  vi.stubEnv("APP_ORIGIN", "http://localhost:3000");
});
describe("session isolation", () => {
  it("rejects tampered, expired and wrong-purpose cookies", () => {
    const created = issue("session");
    expect(verify(created.value, "session")?.id).toBe(created.payload.id);
    expect(verify(created.value + "x", "session")).toBeNull();
    expect(verify(created.value, "nonce")).toBeNull();
    vi.spyOn(Date, "now").mockReturnValue((created.payload.expires + 1) * 1000);
    expect(verify(created.value, "session")).toBeNull();
    vi.restoreAllMocks();
  });
  it("binds CSRF to a specific session and exact origin", () => {
    const one = issue("session").payload;
    const two = issue("session").payload;
    const request = new NextRequest("http://localhost:3000/api/v1/meetings", {
      method: "POST",
      headers: { Origin: "http://localhost:3000", "x-csrf-token": csrf(one) },
    });
    expect(() => requireCsrf(request, one)).not.toThrow();
    expect(() => requireCsrf(request, two)).toThrow();
    expect(() =>
      sameOrigin(
        new NextRequest(request.url, {
          headers: { Origin: "https://evil.example" },
        }),
        true,
      ),
    ).toThrow();
    expect(() => sameOrigin(new NextRequest(request.url), true)).toThrow();
  });
  it("only proxies explicit route and method pairs", () => {
    expect(allowedRoute("meetings", "GET")).toBe(true);
    for (const path of [
      "demo/session",
      "../health/live",
      "https://evil.example",
      "meetings//",
      "meetings/%2e%2e",
    ])
      expect(allowedRoute(path, "GET")).toBe(false);
    expect(allowedRoute("me", "DELETE")).toBe(false);
  });
});

describe("bounded streaming bodies", () => {
  it("rejects a stream that exceeds its allowance without Content-Length", async () => {
    const { boundedBody } = await import("@/lib/bff");
    let cancelled = false;
    const stream = new ReadableStream<Uint8Array>({
      pull(controller) {
        controller.enqueue(new Uint8Array(1024));
      },
      cancel() {
        cancelled = true;
      },
    });
    await expect(boundedBody(new Response(stream), 2048)).rejects.toThrow(
      "too large",
    );
    expect(cancelled).toBe(true);
    expect(await boundedBody(new Response("😀"), 4)).toHaveLength(4);
  });
});
