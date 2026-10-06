"use client";
import { Pause, Play, RotateCcw, RotateCw } from "lucide-react";
import { timestamp } from "@/lib/time";
import type { Meeting } from "@/lib/types";
import type { PlayerState } from "./use-player";
export function Player({
  player,
  meeting,
}: {
  player: PlayerState;
  meeting: Meeting;
}) {
  const { audio, ...p } = player;
  return (
    <section
      className="notebook-player"
      aria-label="Meeting player"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        if (event.key === " " || event.key.toLowerCase() === "k") {
          event.preventDefault();
          void p.toggle();
        }
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          p.seek(p.time - 10000);
        }
        if (event.key === "ArrowRight") {
          event.preventDefault();
          p.seek(p.time + 10000);
        }
      }}
    >
      {meeting.media_mode === "sample" && (
        <audio
          ref={audio}
          src="/audio/welcome.m4a"
          preload="metadata"
          onEnded={() => p.setPlaying(false)}
          onPause={() => p.setPlaying(false)}
          onPlay={() => p.setPlaying(true)}
          onError={() =>
            p.setError("Sample audio is unavailable. Reload to retry.")
          }
        />
      )}
      <div className="player-mode">
        <strong>
          {meeting.media_mode === "sample"
            ? "Sample audio"
            : "Simulated playback"}
        </strong>
        <span>
          {meeting.media_mode === "sample"
            ? "Original demonstration tones · not a recording"
            : "Transcript timing · no recording attached"}
        </span>
      </div>
      <div className="player-controls">
        <button
          className="icon-button"
          aria-label="Back 10 seconds"
          onClick={() => p.seek(p.time - 10000)}
        >
          <RotateCcw size={18} />
        </button>
        <button
          className="play-button"
          aria-label={p.playing ? "Pause" : "Play"}
          onClick={() => void p.toggle()}
        >
          {p.playing ? <Pause size={19} /> : <Play size={19} />}
        </button>
        <button
          className="icon-button"
          aria-label="Forward 10 seconds"
          onClick={() => p.seek(p.time + 10000)}
        >
          <RotateCw size={18} />
        </button>
        <output className="elapsed">
          {timestamp(p.time)} / {timestamp(meeting.duration_ms)}
        </output>
        <select
          aria-label="Playback speed"
          value={p.speed}
          onChange={(e) => p.setSpeed(Number(e.target.value))}
        >
          {[0.5, 0.75, 1, 1.25, 1.5, 2].map((speed) => (
            <option key={speed} value={speed}>
              {speed}×
            </option>
          ))}
        </select>
      </div>
      <input
        className="player-range"
        aria-label="Seek meeting"
        type="range"
        min={0}
        max={meeting.duration_ms}
        step={100}
        value={p.time}
        aria-valuetext={`${timestamp(p.time)} of ${timestamp(meeting.duration_ms)}`}
        onChange={(e) => p.seek(Number(e.target.value))}
      />
      {p.range && (
        <span className="soundbite-state">
          Soundbite {timestamp(p.range.start)}–{timestamp(p.range.end)}{" "}
          {p.time >= p.range.end ? "· Complete" : ""}{" "}
          <button onClick={p.clearRange}>Exit interval</button>
        </span>
      )}
      {p.time >= meeting.duration_ms && (
        <span className="muted">Playback complete</span>
      )}
      {p.error && <p role="alert">{p.error}</p>}
    </section>
  );
}
