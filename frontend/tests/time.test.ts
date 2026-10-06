import { expect, it } from "vitest";
import { dateBoundary, timestamp } from "@/lib/time";
it("converts calendar boundaries through timezone and daylight-saving changes", () => {
  expect(dateBoundary("2026-10-06", "Asia/Kolkata")).toBe(
    "2026-10-05T18:30:00.000Z",
  );
  expect(dateBoundary("2026-03-08", "America/New_York")).toBe(
    "2026-03-08T05:00:00.000Z",
  );
  expect(dateBoundary("2026-03-08", "America/New_York", true)).toBe(
    "2026-03-09T04:00:00.000Z",
  );
  expect(timestamp(3661000)).toBe("1:01:01");
});
