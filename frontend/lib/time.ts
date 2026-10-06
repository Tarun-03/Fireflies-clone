export function timestamp(ms: number) {
  const seconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(seconds / 3600);
  return `${hours ? `${hours}:` : ""}${String(Math.floor(seconds / 60) % 60).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
export function dateLabel(value: string, timezone = "Asia/Kolkata") {
  return new Intl.DateTimeFormat("en", {
    timeZone: timezone,
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
export function timeLabel(value: string, timezone = "Asia/Kolkata") {
  return new Intl.DateTimeFormat("en", {
    timeZone: timezone,
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}
export function dateBoundary(
  date: string,
  timezone: string,
  next = false,
): string {
  const target = new Date(`${date}T00:00:00Z`);
  if (next) target.setUTCDate(target.getUTCDate() + 1);
  const expected = target.getTime();
  let instant = expected;
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  });
  for (let i = 0; i < 4; i++) {
    const parts = Object.fromEntries(
      formatter
        .formatToParts(new Date(instant))
        .map((part) => [part.type, part.value]),
    );
    const actual = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour),
      Number(parts.minute),
      Number(parts.second),
    );
    const delta = expected - actual;
    instant += delta;
    if (!delta) break;
  }
  return new Date(instant).toISOString();
}
