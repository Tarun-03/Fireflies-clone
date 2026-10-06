import type { TimelineEntry } from "@/lib/types";
export function locate(timeline: TimelineEntry[], time: number) {
  let low = 0,
    high = timeline.length - 1,
    position = -1;
  while (low <= high) {
    const middle = (low + high) >>> 1;
    if (timeline[middle].start_ms <= time) {
      position = middle;
      low = middle + 1;
    } else high = middle - 1;
  }
  const segment = timeline[position];
  return { segment, gap: !segment || time >= segment.end_ms };
}
/** A monotonic clock; callers supply performance.now(), never wall-clock dates. */
export class PlaybackClock {
  private position = 0;
  private anchor = 0;
  playing = false;
  speed = 1;
  constructor(readonly duration: number) {}
  read(now: number) {
    const value = Math.min(
      this.duration,
      this.position + (this.playing ? (now - this.anchor) * this.speed : 0),
    );
    if (value >= this.duration) {
      this.position = this.duration;
      this.playing = false;
    }
    return value;
  }
  seek(value: number, now: number) {
    this.position = Math.max(0, Math.min(this.duration, value));
    this.anchor = now;
  }
  pause(now: number) {
    this.position = this.read(now);
    this.playing = false;
  }
  play(now: number) {
    if (this.position >= this.duration) this.position = 0;
    this.anchor = now;
    this.playing = true;
  }
  setSpeed(value: number, now: number) {
    this.position = this.read(now);
    this.anchor = now;
    this.speed = value;
  }
}
