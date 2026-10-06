"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Maximize2, Minimize2 } from "lucide-react";
import { useApi } from "@/components/providers";
import { ErrorNotice } from "@/components/dialog";
import { Avatar } from "@/components/avatar";
import { dateLabel, timeLabel } from "@/lib/time";
import type { Meeting, Profile, TimelineEntry } from "@/lib/types";
import { MeetingMenu } from "@/features/library/meeting-menu";
import { NotebookTools } from "./annotations-panel";
import { Player } from "./player";
import { usePlayer } from "./use-player";
import { TranscriptPanel } from "./transcript";
import { NotesPanel } from "./notes";
export function Notebook({ id }: { id: string }) {
  const meeting = useApi<Meeting>(`meetings/${id}`);
  const profile = useApi<Profile>("me");
  if (meeting.isError)
    return (
      <div className="empty-state">
        <h1>Notebook unavailable</h1>
        <ErrorNotice error={meeting.error} />
        <button onClick={() => meeting.refetch()}>Try again</button>
        <Link href="/">Back to meetings</Link>
      </div>
    );
  if (!meeting.data || !profile.data)
    return (
      <div className="skeleton-list" aria-label="Loading notebook">
        <div className="skeleton-row" />
        <div className="skeleton-row" />
      </div>
    );
  return (
    <NotebookContent key={id} meeting={meeting.data} profile={profile.data} />
  );
}
function NotebookContent({
  meeting,
  profile,
}: {
  meeting: Meeting;
  profile: Profile;
}) {
  const timeline = useApi<TimelineEntry[]>(`meetings/${meeting.id}/timeline`);
  const params = useSearchParams();
  const [tab, setTab] = useState("summary");
  const [expanded, setExpanded] = useState(false);
  const player = usePlayer(
    meeting.duration_ms,
    meeting.media_mode === "sample",
    profile.preferences.player_speed,
  );
  return (
    <div className={`notebook ${expanded ? "transcript-expanded" : ""}`}>
      <Link className="back-link" href="/">
        <ArrowLeft size={16} /> All meetings
      </Link>
      <header className="notebook-heading">
        <div>
          <h1>{meeting.title}</h1>
          <div className="meeting-meta">
            <span>
              {dateLabel(meeting.occurred_at, profile.preferences.timezone)} ·{" "}
              {timeLabel(meeting.occurred_at, profile.preferences.timezone)}
            </span>
            <span>{Math.round(meeting.duration_ms / 60000)} min</span>
            <span>
              {meeting.source === "seeded"
                ? "Synthetic sample"
                : meeting.source}
            </span>
          </div>
        </div>
        <MeetingMenu meeting={meeting} />
      </header>
      <div className="notebook-metadata">
        <div className="avatar-stack">
          {meeting.participants.map((person) => (
            <Avatar name={person.display_name} small key={person.id} />
          ))}
        </div>
        <span className="muted">
          {meeting.participants.length} participants
        </span>
        {meeting.tags.map((tag) => (
          <span key={tag.id} className={`tag tag-${tag.color}`}>
            {tag.name}
          </span>
        ))}
        <button
          className="expand-notebook icon-button"
          aria-label={expanded ? "Show split view" : "Focus transcript"}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
        </button>
      </div>
      <div className="notebook-tabs" role="tablist" aria-label="Notebook view">
        {["summary", "transcript"].map((value) => (
          <button
            key={value}
            role="tab"
            aria-selected={tab === value}
            onClick={() => setTab(value)}
          >
            {value === "summary" ? "Summary" : "Transcript"}
          </button>
        ))}
      </div>
      <ErrorNotice error={timeline.error} />
      <div className="notebook-body">
        <div className={`notebook-panels mobile-${tab}`}>
          <NotesPanel
            id={meeting.id}
            timeline={timeline.data ?? []}
            seek={player.seek}
          />
          <TranscriptPanel
            id={meeting.id}
            timeline={timeline.data ?? []}
            player={player}
            initialSegment={params.get("segment")}
          />
        </div>
        <NotebookTools
          id={meeting.id}
          duration={meeting.duration_ms}
          timeline={timeline.data ?? []}
          player={player}
        />
      </div>
      <Player player={player} meeting={meeting} />
    </div>
  );
}
