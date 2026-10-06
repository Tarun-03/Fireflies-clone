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
  useEffect(() => {
    clock.setSpeed(speed, performance.now());
    if (audio.current) audio.current.playbackRate = speed;
  }, [clock, speed]);
  useEffect(() => {
    let frame = 0;
    function tick() {
      const next = sample
        ? (audio.current?.currentTime ?? 0) * 1000
        : clock.read(performance.now());
      setTime(Math.min(duration, next));
      if (!sample && !clock.playing) setPlaying(false);
      frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [clock, duration, sample]);
  const seek = useCallback(
    (value: number) => {
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
  async function toggle() {
    setError("");
    if (playing) {
      pause();
      return;
    }
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
  return {
    audio,
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
