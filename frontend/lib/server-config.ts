export function serverConfig() {
  const origin = process.env.APP_ORIGIN ?? "http://localhost:3000";
  const production = process.env.APP_ENV === "production";
  const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  const serviceToken = process.env.INTERNAL_API_TOKEN ?? "";
  const signingSecret = process.env.SESSION_SIGNING_SECRET ?? "";
  const parsedOrigin = new URL(origin);
  const parsedBackend = new URL(backend);
  if (
    serviceToken.length < 32 ||
    signingSecret.length < 32 ||
    serviceToken === signingSecret
  )
    throw new Error(
      "Configure distinct server secrets of at least 32 characters",
    );
  if (
    parsedOrigin.origin !== origin ||
    parsedBackend.username ||
    parsedBackend.password ||
    parsedBackend.search ||
    parsedBackend.hash
  )
    throw new Error(
      "Configure fixed origins without credentials or query strings",
    );
  if (
    production &&
    (parsedOrigin.protocol !== "https:" || parsedBackend.protocol !== "https:")
  )
    throw new Error("Production services require HTTPS");
  if (!["http:", "https:"].includes(parsedBackend.protocol))
    throw new Error("Invalid backend protocol");
  return {
    origin,
    backend: parsedBackend.origin,
    serviceToken,
    signingSecret,
    production,
  };
}
