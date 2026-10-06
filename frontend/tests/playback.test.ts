import { describe, expect, it } from "vitest";
import { PlaybackClock, locate } from "@/features/notebook/playback";
describe("monotonic playback", () => {
  it("preserves paused seeks, speed anchors, clamping, and end/replay", () => {
    const c = new PlaybackClock(10000);
    c.seek(2000, 0);
    expect(c.read(3000)).toBe(2000);
    c.play(3000);
    expect(c.read(4000)).toBe(3000);
    c.setSpeed(2, 4000);
    expect(c.read(5000)).toBe(5000);
    c.pause(5000);
    expect(c.read(9000)).toBe(5000);
    c.seek(-99, 9000);
    expect(c.read(9000)).toBe(0);
    c.play(10000);
    expect(c.read(16000)).toBe(10000);
    expect(c.playing).toBe(false);
    c.play(16000);
    expect(c.read(16500)).toBe(1000);
    c.seek(50000, 16500);
    expect(c.read(17000)).toBe(10000);
  });
  it("selects latest start then ordinal and marks gaps", () => {
    const timeline = [
      { public_id: "a", start_ms: 1000, end_ms: 5000, ordinal: 0 },
      { public_id: "b", start_ms: 2000, end_ms: 4000, ordinal: 1 },
      { public_id: "c", start_ms: 2000, end_ms: 3500, ordinal: 2 },
    ];
    expect(locate(timeline, 500)).toEqual({ segment: undefined, gap: true });
    expect(locate(timeline, 2500)).toEqual({
      segment: timeline[2],
      gap: false,
    });
    expect(locate(timeline, 3700)).toEqual({
      segment: timeline[1],
      gap: false,
    });
    expect(locate(timeline, 4500)).toEqual({
      segment: timeline[0],
      gap: false,
    });
    expect(locate(timeline, 6000)).toEqual({ segment: timeline[2], gap: true });
    const long = Array.from({ length: 3000 }, (_, i) => ({
      public_id: String(i),
      start_ms: i * 1000,
      end_ms: i * 1000 + 900,
      ordinal: i,
    }));
    expect(locate(long, 2980500).segment?.public_id).toBe("2980");
  });
});
