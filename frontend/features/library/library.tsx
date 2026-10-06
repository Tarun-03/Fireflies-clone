"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  CalendarDays,
  Clock,
  FileText,
  Search,
  SlidersHorizontal,
  Upload,
  X,
} from "lucide-react";
import { Avatar } from "@/components/avatar";
import { ErrorNotice } from "@/components/dialog";
import { useApi } from "@/components/providers";
import { dateBoundary, dateLabel, timeLabel } from "@/lib/time";
import type { Meeting, Page, Participant, Profile, Tag } from "@/lib/types";
import { MeetingMenu } from "./meeting-menu";

export function Library({ uploads = false }: { uploads?: boolean }) {
  const params = useSearchParams();
  const router = useRouter();
  const profile = useApi<Profile>("me");
  const people = useApi<Page<Participant>>("participants");
  const tags = useApi<Page<Tag>>("tags");
  const timezone = profile.data?.preferences.timezone ?? "Asia/Kolkata";
  const query = new URLSearchParams(params.toString());
  query.delete("from");
  query.delete("to");
  query.delete("tab");
  if (params.get("from"))
    query.set("after", dateBoundary(params.get("from")!, timezone));
  if (params.get("to"))
    query.set("before", dateBoundary(params.get("to")!, timezone, true));
  if (uploads) query.set("source", "uploaded");
  const result = useApi<Page<Meeting>>(`meetings?${query.toString()}`);
  function change(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "cursor") next.delete("cursor");
    router.push(`${uploads ? "/uploads" : "/"}?${next}`);
  }
  function changeMany(values: Record<string, string>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(values)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    next.delete("cursor");
    router.push(`${uploads ? "/uploads" : "/"}?${next}`);
  }
  function preset(days: number) {
    if (!days) {
      changeMany({ from: "", to: "" });
      return;
    }
    const today = new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
    const start = new Date(`${today}T12:00:00Z`);
    start.setUTCDate(start.getUTCDate() - days + 1);
    changeMany({ from: start.toISOString().slice(0, 10), to: today });
  }
  const filtered = [
    "q",
    "participant",
    "tag",
    "from",
    "to",
    "minimum",
    "maximum",
  ].some((key) => params.has(key));
  let lastDate = "";
  return (
    <div className="library">
      <div className="page-heading">
        <div>
          <h1>{uploads ? "Uploads" : "Meetings"}</h1>
          <p className="muted">
            {uploads
              ? "Your imported conversations, ready to revisit."
              : "Every conversation. Right where you left it."}
          </p>
        </div>
        <span className="subtle-badge">Private workspace</span>
      </div>
      <div className="tabs">
        <button
          className={params.get("tab") !== "mine" ? "active" : ""}
          onClick={() => change("tab", "")}
        >
          {uploads ? "Imported meetings" : "All meetings"}
        </button>
        {!uploads && (
          <button
            className={params.get("tab") === "mine" ? "active" : ""}
            onClick={() => change("tab", "mine")}
          >
            My meetings
          </button>
        )}
      </div>
      <div className="filter-toolbar">
        <div className="search-field">
          <Search size={17} />
          <input
            aria-label="Search meeting titles"
            placeholder="Search meeting titles…"
            value={params.get("q") ?? ""}
            maxLength={200}
            onChange={(event) => change("q", event.target.value)}
          />
        </div>
        <label className="compact-select">
          <span className="sr-only">Participant</span>
          <select
            aria-label="Filter by participant"
            value={params.get("participant") ?? ""}
            onChange={(event) => change("participant", event.target.value)}
          >
            <option value="">All participants</option>
            {people.data?.items.map((person) => (
              <option value={person.id} key={person.id}>
                {person.display_name}
              </option>
            ))}
          </select>
        </label>
        <label className="compact-select">
          <span className="sr-only">Tag</span>
          <select
            aria-label="Filter by tag"
            value={params.get("tag") ?? ""}
            onChange={(event) => change("tag", event.target.value)}
          >
            <option value="">All tags</option>
            {tags.data?.items.map((tag) => (
              <option value={tag.id} key={tag.id}>
                {tag.name}
              </option>
            ))}
          </select>
        </label>
        <details className="filter-popover">
          <summary>
            <SlidersHorizontal size={16} />
            Filters
          </summary>
          <div className="filter-fields">
            <label>
              Date preset
              <select
                aria-label="Date preset"
                defaultValue="custom"
                onChange={(event) => {
                  if (event.target.value !== "custom")
                    preset(Number(event.target.value));
                }}
              >
                <option value="custom">Custom range</option>
                <option value="0">Any time</option>
                <option value="1">Today</option>
                <option value="7">Last 7 days</option>
                <option value="30">Last 30 days</option>
              </select>
            </label>
            <label>
              From date
              <input
                type="date"
                value={params.get("from") ?? ""}
                onChange={(event) => change("from", event.target.value)}
              />
            </label>
            <label>
              Through date
              <input
                type="date"
                value={params.get("to") ?? ""}
                onChange={(event) => change("to", event.target.value)}
              />
            </label>
            <label>
              Duration
              <select
                value={`${params.get("minimum") ?? ""}:${params.get("maximum") ?? ""}`}
                onChange={(event) => {
                  const [minimum, maximum] = event.target.value.split(":");
                  changeMany({ minimum, maximum });
                }}
              >
                <option value=":">Any duration</option>
                <option value=":900000">Under 15 minutes</option>
                <option value="900000:1800000">15–30 minutes</option>
                <option value="1800000:3600000">30–60 minutes</option>
                <option value="3600000:">60+ minutes</option>
              </select>
            </label>
            <small>Dates shown in {timezone}</small>
          </div>
        </details>
        <select
          className="sort-select"
          aria-label="Sort meetings"
          value={params.get("sort") ?? "recent"}
          onChange={(event) => change("sort", event.target.value)}
        >
          <option value="recent">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="title">Title A–Z</option>
        </select>
      </div>
      {filtered && (
        <div className="filter-chips">
          {["q", "participant", "tag", "from", "to", "minimum", "maximum"]
            .filter((key) => params.has(key))
            .map((key) => (
              <button key={key} onClick={() => change(key, "")}>
                {key === "participant"
                  ? (people.data?.items.find((p) => p.id === params.get(key))
                      ?.display_name ?? "Participant")
                  : key === "tag"
                    ? (tags.data?.items.find((t) => t.id === params.get(key))
                        ?.name ?? "Tag")
                    : `${key}: ${params.get(key)}`}
                <X size={12} />
              </button>
            ))}
          <button onClick={() => router.push(uploads ? "/uploads" : "/")}>
            Clear all
          </button>
        </div>
      )}
      <ErrorNotice error={result.error} />
      {result.isError && (
        <button onClick={() => result.refetch()}>Try again</button>
      )}
      {!result.data && !result.isError ? (
        <div aria-label="Loading meetings" className="skeleton-list">
          {[1, 2, 3, 4, 5].map((item) => (
            <div className="skeleton-row" key={item} />
          ))}
        </div>
      ) : result.data?.items.length === 0 ? (
        <div className="empty-state">
          <CalendarDays size={32} />
          <h2>{filtered ? "No matching meetings" : "A little quiet here"}</h2>
          <p>
            {filtered
              ? "Try adjusting your filters or clearing your search."
              : "Create or import a meeting to start your notebook."}
          </p>
          {filtered && (
            <button onClick={() => router.push(uploads ? "/uploads" : "/")}>
              Clear filters
            </button>
          )}
        </div>
      ) : (
        <div className="meeting-list">
          {result.data?.items.map((meeting) => {
            const date = dateLabel(meeting.occurred_at, timezone);
            const showDate = date !== lastDate;
            lastDate = date;
            return (
              <div key={meeting.id}>
                {showDate && <h2 className="date-group">{date}</h2>}
                <article className="meeting-row">
                  <div className="source-icon">
                    {meeting.source === "uploaded" ? (
                      <Upload size={19} />
                    ) : (
                      <FileText size={19} />
                    )}
                  </div>
                  <div className="meeting-row-main">
                    <Link
                      className="meeting-title"
                      href={`/meetings/${meeting.id}`}
                    >
                      {meeting.title}
                    </Link>
                    <div className="meeting-meta">
                      <span>
                        <Clock size={13} />
                        {timeLabel(meeting.occurred_at, timezone)}
                      </span>
                      <span>{Math.round(meeting.duration_ms / 60000)} min</span>
                      <span>
                        {meeting.source === "seeded"
                          ? "Synthetic sample"
                          : meeting.source}
                      </span>
                    </div>
                  </div>
                  <div className="row-tags">
                    {meeting.tags.map((tag) => (
                      <button
                        className={`tag tag-${tag.color}`}
                        key={tag.id}
                        onClick={() => change("tag", tag.id)}
                      >
                        {tag.name}
                      </button>
                    ))}
                  </div>
                  <div className="avatar-stack">
                    {meeting.participants.slice(0, 4).map((person) => (
                      <Avatar
                        name={person.display_name}
                        small
                        key={person.id}
                      />
                    ))}
                    {meeting.participants.length > 4 && (
                      <span className="extra-people">
                        +{meeting.participants.length - 4}
                      </span>
                    )}
                  </div>
                  <MeetingMenu meeting={meeting} />
                </article>
              </div>
            );
          })}
        </div>
      )}
      <div className="pagination">
        <span className="muted">
          {result.data?.items.length ?? 0} meetings on this page
        </span>
        <div>
          {params.has("cursor") && (
            <button onClick={() => change("cursor", "")}>First page</button>
          )}
          <button
            disabled={!result.data?.has_more}
            onClick={() => change("cursor", result.data?.next_cursor ?? "")}
          >
            Next page
          </button>
        </div>
      </div>
      <p className="library-footnote">
        Your demo is yours to explore. All sample meetings are synthetic.
      </p>
    </div>
  );
}
