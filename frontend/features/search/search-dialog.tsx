"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Search, X } from "lucide-react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useApi, useAllPages } from "@/components/providers";
import { Marked } from "@/features/notebook/transcript";
import { dateLabel, timestamp } from "@/lib/time";
import type { Page, Participant, SearchHit, Tag } from "@/lib/types";
export function SearchDialog({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [tag, setTag] = useState("");
  const [participant, setParticipant] = useState("");
  const [kind, setKind] = useState("");
  const [cursor, setCursor] = useState("");
  const [after, setAfter] = useState("");
  const [before, setBefore] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), 250);
    return () => clearTimeout(timer);
  }, [query]);
  const tags = useApi<Page<Tag>>("tags");
  const people = useAllPages<Participant>("participants");
  const params = new URLSearchParams({ q: debounced });
  if (tag) params.set("tag", tag);
  if (participant) params.set("participant", participant);
  if (kind) params.set("kind", kind);
  if (cursor) params.set("cursor", cursor);
  if (after) params.set("after", `${after}T00:00:00Z`);
  if (before)
    params.set(
      "before",
      new Date(Date.parse(`${before}T00:00:00Z`) + 86400000).toISOString(),
    );
  const result = useApi<Page<SearchHit>>(
    `search?${params}`,
    Boolean(debounced.trim()),
  );
  return (
    <Dialog
      wide
      title="Search meetings"
      description="Search titles and transcript evidence across your private workspace."
      open
      onOpenChange={onClose}
    >
      <div className="search-field">
        <Search size={18} />
        <input
          aria-label="Search all meetings"
          maxLength={200}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setCursor("");
          }}
          placeholder="Search your conversations…"
          autoFocus
        />
        {query && (
          <button
            className="icon-button"
            aria-label="Clear search"
            onClick={() => {
              setQuery("");
              setCursor("");
            }}
          >
            <X size={16} />
          </button>
        )}
      </div>
      <div className="global-search-filters">
        <select
          aria-label="Search in"
          value={kind}
          onChange={(e) => {
            setKind(e.target.value);
            setCursor("");
          }}
        >
          <option value="">Titles and transcript</option>
          <option value="title">Titles only</option>
          <option value="transcript">Transcript only</option>
        </select>
        <select
          aria-label="Search tag"
          value={tag}
          onChange={(e) => {
            setTag(e.target.value);
            setCursor("");
          }}
        >
          <option value="">All tags</option>
          {tags.data?.items.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Search participant"
          value={participant}
          onChange={(e) => {
            setParticipant(e.target.value);
            setCursor("");
          }}
        >
          <option value="">All participants</option>
          {people.data?.items.map((p) => (
            <option key={p.id} value={p.id}>
              {p.display_name}
            </option>
          ))}
        </select>
      </div>
      <div className="form-grid">
        <label>
          From date (UTC)
          <input
            type="date"
            value={after}
            onChange={(e) => {
              setAfter(e.target.value);
              setCursor("");
            }}
          />
        </label>
        <label>
          Through date (UTC)
          <input
            type="date"
            value={before}
            onChange={(e) => {
              setBefore(e.target.value);
              setCursor("");
            }}
          />
        </label>
      </div>
      <ErrorNotice error={result.error} />
      <div className="search-results">
        {!query.trim() ? (
          <p className="muted">Type a topic, a phrase, or a meeting title.</p>
        ) : query !== debounced || result.isLoading ? (
          <p>Searching…</p>
        ) : result.data?.items.length === 0 ? (
          <p>No matching evidence. Try another phrase or clear a filter.</p>
        ) : (
          result.data?.items.map((hit) => (
            <Link
              className="global-search-hit"
              key={hit.id}
              onClick={onClose}
              href={`/meetings/${hit.meeting_id}${hit.segment_id ? `?segment=${hit.segment_id}` : ""}`}
            >
              <span>
                <strong>{hit.title}</strong>
                <small>
                  {dateLabel(hit.occurred_at)} ·{" "}
                  {hit.kind === "title"
                    ? "Title match"
                    : `${hit.speaker_name ?? "Unknown speaker"} · ${timestamp(hit.timestamp_ms ?? 0)}`}
                </small>
                <span className="search-snippet">
                  <Marked text={hit.snippet} ranges={hit.ranges} />
                </span>
              </span>
            </Link>
          ))
        )}
      </div>
      {debounced && (
        <div className="pagination">
          <button disabled={!cursor} onClick={() => setCursor("")}>
            First results
          </button>
          <button
            disabled={!result.data?.next_cursor}
            onClick={() => setCursor(result.data?.next_cursor ?? "")}
          >
            More results
          </button>
        </div>
      )}
    </Dialog>
  );
}
