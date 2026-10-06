"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { PlaybackClock } from "./playback";
export function usePlayer(
  duration: number,
  sample: boolean,
  initialSpeed: number,
) {
  const [clock] = useState(() => new PlaybackClock(duration));
  const audio = useRef<HTMLAudioElement>(null);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(initialSpeed);
  const [error, setError] = useState("");
  const [follow, setFollow] = useState(true);
  const [range, setRange] = useState<{ start: number; end: number } | null>(
    null,
  );
  const boundary = useRef<number | null>(null);
  useEffect(() => {
    clock.setSpeed(speed, performance.now());
    if (audio.current) audio.current.playbackRate = speed;
  }, [clock, speed]);
  useEffect(() => {
    let frame = 0;
    function tick() {
      let next = sample
        ? (audio.current?.currentTime ?? 0) * 1000
        : clock.read(performance.now());
      if (boundary.current !== null && next >= boundary.current) {
        next = boundary.current;
        boundary.current = null;
        if (sample && audio.current) {
          audio.current.pause();
          audio.current.currentTime = next / 1000;
        } else {
          clock.seek(next, performance.now());
          clock.pause(performance.now());
        }
        setPlaying(false);
      }
      setTime(Math.min(duration, next));
      if (!sample && !clock.playing) setPlaying(false);
      frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [clock, duration, sample]);
  const seek = useCallback(
    (value: number) => {
      boundary.current = null;
      setRange(null);
      setFollow(true);
      const target = Math.max(0, Math.min(duration, value));
      if (sample && audio.current) audio.current.currentTime = target / 1000;
      else clock.seek(target, performance.now());
      setTime(target);
    },
    [clock, duration, sample],
  );
  function pause() {
    if (sample) audio.current?.pause();
    else clock.pause(performance.now());
    setPlaying(false);
  }
  async function play() {
    setError("");
    if (sample && audio.current) {
      if (audio.current.ended) audio.current.currentTime = 0;
      try {
        await audio.current.play();
        setPlaying(true);
      } catch {
        setError(
          "Audio could not start. Retry playback or check your browser’s audio settings.",
        );
      }
    } else {
      clock.play(performance.now());
      setPlaying(true);
    }
  }
  async function playRange(start: number, end: number) {
    seek(start);
    boundary.current = Math.min(duration, end);
    setRange({ start, end: Math.min(duration, end) });
    await play();
  }
  async function toggle() {
    if (playing) {
      pause();
      return;
    }
    if (range && time >= range.end) {
      await playRange(range.start, range.end);
    } else await play();
  }
  function clearRange() {
    boundary.current = null;
    setRange(null);
  }
  return {
    audio,
    follow,
    setFollow,
    range,
    playRange,
    clearRange,
    time,
    playing,
    speed,
    setSpeed,
    seek,
    pause,
    toggle,
    error,
    setError,
    setPlaying,
  };
}
export type PlayerState = ReturnType<typeof usePlayer>;
