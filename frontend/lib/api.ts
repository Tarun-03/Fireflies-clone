import { z } from "zod";
let csrfToken = "";
const tokenSchema = z.object({ csrf_token: z.string(), ready: z.boolean() });
const errorSchema = z.object({
  error: z.object({ message: z.string(), code: z.string() }),
});
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
async function result<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json();
  if (!response.ok) {
    const parsed = errorSchema.safeParse(data);
    throw new ApiError(
      response.status,
      parsed.success ? parsed.data.error.code : "unavailable",
      parsed.success
        ? parsed.data.error.message
        : "Unable to load your workspace. Please retry.",
    );
  }
  return data as T;
}
export async function bootstrap() {
  const initial = tokenSchema.parse(
    await result<unknown>(
      await fetch("/api/session/csrf", { cache: "no-store" }),
    ),
  );
  const session = tokenSchema.parse(
    await result<unknown>(
      await fetch("/api/session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": initial.csrf_token,
        },
        body: "{}",
      }),
    ),
  );
  csrfToken = session.csrf_token;
  return true;
}
export async function api<T>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    version?: number;
    key?: string;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const headers = new Headers();
  if (options.body !== undefined)
    headers.set("Content-Type", "application/json");
  if (options.method && options.method !== "GET")
    headers.set("X-CSRF-Token", csrfToken);
  if (options.version !== undefined)
    headers.set("If-Match", String(options.version));
  if (options.key) headers.set("Idempotency-Key", options.key);
  try {
    return await result<T>(
      await fetch(`/api/v1/${path}`, {
        method: options.method,
        headers,
        body:
          options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: options.signal,
        cache: "no-store",
      }),
    );
  } catch (error) {
    if (
      error instanceof ApiError ||
      (error instanceof DOMException && error.name === "AbortError")
    )
      throw error;
    throw new ApiError(
      503,
      "unavailable",
      "Cannot reach your workspace. Check your connection and retry.",
    );
  }
}
