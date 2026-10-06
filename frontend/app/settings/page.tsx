"use client";
import { useState } from "react";
import { useAction, useApi } from "@/components/providers";
import { ErrorNotice } from "@/components/dialog";
import type { Preferences, Profile } from "@/lib/types";
export default function SettingsPage() {
  const profile = useApi<Profile>("me");
  return (
    <div className="settings-page">
      <div className="page-heading">
        <div>
          <h1>Settings</h1>
          <p className="muted">Make your workspace feel like yours.</p>
        </div>
      </div>
      <ErrorNotice error={profile.error} />
      {profile.data ? (
        <SettingsForm
          preferences={profile.data.preferences}
          key={profile.data.preferences.version}
        />
      ) : (
        <p>Loading preferences…</p>
      )}
      <section className="settings-section">
        <h2>About this workspace</h2>
        <p>
          This is an unofficial, original Fireflies-inspired assignment demo. It
          is not affiliated with Fireflies.
        </p>
        <p>
          Sample people and conversations are synthetic. Your browser has an
          isolated anonymous workspace; this is not a verified account. Clearing
          your session cookie or its expiry after 30 days starts a new workspace
          and does not delete the old records.
        </p>
        <p>
          Meeting bots, external integrations, and team collaboration are coming
          soon. Uploaded transcripts use labelled simulated playback.
        </p>
        <p>
          {profile.data?.ai_available
            ? "AI is available. Selecting AI mode sends selected meeting excerpts to OpenAI."
            : "Extractive mode is available without an API key. It returns meeting evidence without generated reasoning."}
        </p>
      </section>
    </div>
  );
}
function SettingsForm({ preferences }: { preferences: Preferences }) {
  const [theme, setTheme] = useState(preferences.theme);
  const [timezone, setTimezone] = useState(preferences.timezone);
  const [speed, setSpeed] = useState(preferences.player_speed);
  const [motion, setMotion] = useState(preferences.reduced_motion);
  const action = useAction();
  return (
    <form
      className="settings-section form-stack"
      onSubmit={(event) => {
        event.preventDefault();
        action
          .mutateAsync({
            path: "me/preferences",
            method: "PATCH",
            version: preferences.version,
            body: {
              theme,
              timezone,
              player_speed: speed,
              reduced_motion: motion,
            },
            message: "Preferences saved",
          })
          .then(
            () => {
              document.documentElement.dataset.theme = theme;
              document.documentElement.dataset.reducedMotion = String(motion);
              document.cookie = `meeting-motion=${motion}; Path=/; Max-Age=2592000; SameSite=Lax`;
              document.cookie = `meeting-theme=${theme}; Path=/; Max-Age=2592000; SameSite=Lax${location.protocol === "https:" ? "; Secure" : ""}`;
            },
            () => {},
          );
      }}
    >
      <h2>Appearance & playback</h2>
      <label>
        Theme
        <select
          value={theme}
          onChange={(event) =>
            setTheme(event.target.value as Preferences["theme"])
          }
        >
          <option value="system">Use system appearance</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </label>
      <label>
        Display timezone
        <select
          value={timezone}
          onChange={(event) => setTimezone(event.target.value)}
        >
          {[
            ...new Set([
              preferences.timezone,
              "Asia/Kolkata",
              "UTC",
              "America/New_York",
              "America/Los_Angeles",
              "Europe/London",
              "Asia/Tokyo",
            ]),
          ].map((zone) => (
            <option key={zone}>{zone}</option>
          ))}
        </select>
      </label>
      <label>
        Default playback speed
        <select
          value={speed}
          onChange={(event) => setSpeed(Number(event.target.value))}
        >
          {[0.5, 0.75, 1, 1.25, 1.5, 2].map((value) => (
            <option key={value} value={value}>
              {value}×
            </option>
          ))}
        </select>
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={motion}
          onChange={(event) => setMotion(event.target.checked)}
        />
        Reduce motion
      </label>
      <ErrorNotice error={action.error} />
      <div>
        <button className="primary" disabled={action.isPending}>
          {action.isPending ? "Saving…" : "Save preferences"}
        </button>
      </div>
    </form>
  );
}
