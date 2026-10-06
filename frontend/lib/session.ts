import { createHmac, randomUUID, timingSafeEqual } from "node:crypto";
import { z } from "zod";
import { serverConfig } from "./server-config";

const payloadSchema = z
  .object({
    version: z.literal(1),
    id: z.string().uuid(),
    expires: z.number().int().positive(),
    purpose: z.enum(["session", "nonce"]),
  })
  .strict();
export type Session = z.infer<typeof payloadSchema>;

function signature(value: string) {
  return createHmac("sha256", serverConfig().signingSecret)
    .update(value)
    .digest("base64url");
}
export function equal(a: string, b: string) {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
}
export function issue(purpose: Session["purpose"], id = randomUUID()) {
  const seconds = purpose === "session" ? 30 * 24 * 60 * 60 : 10 * 60;
  const payload: Session = {
    version: 1,
    id,
    expires: Math.floor(Date.now() / 1000) + seconds,
    purpose,
  };
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return { value: `${body}.${signature(body)}`, payload, seconds };
}
export function verify(
  value: string | undefined,
  purpose: Session["purpose"],
): Session | null {
  if (!value || value.length > 1000) return null;
  const [body, mac, extra] = value.split(".");
  if (!body || !mac || extra || !equal(signature(body), mac)) return null;
  try {
    const payload = payloadSchema.parse(
      JSON.parse(Buffer.from(body, "base64url").toString("utf8")),
    );
    if (payload.purpose !== purpose || payload.expires <= Date.now() / 1000)
      return null;
    return payload;
  } catch {
    return null;
  }
}
export function csrf(session: Session) {
  return signature(`csrf:${session.purpose}:${session.id}:${session.expires}`);
}
export function cookieName(purpose: Session["purpose"]) {
  return `${serverConfig().production ? "__Host-" : "dev-"}meeting-${purpose}`;
}
export function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: serverConfig().production,
    path: "/",
    maxAge,
  };
}
