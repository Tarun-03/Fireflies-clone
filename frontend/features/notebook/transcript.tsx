"use client";
import { useEffect, useRef, useState } from "react";
import { Search, TextCursorInput } from "lucide-react";
import { useApi } from "@/components/providers";
import { ErrorNotice } from "@/components/dialog";
import { Avatar } from "@/components/avatar";
import { timestamp } from "@/lib/time";
import type {
  Segment,
  Speaker,
  TimelineEntry,
  Transcript as TranscriptData,
  TranscriptSearch,
} from "@/lib/types";
import { AnnotationCreate } from "./annotation-create";
import { selectedRange, highlightChunks } from "./selection";
import { SegmentEditor } from "./segment-editor";
import { locate } from "./playback";
import type { PlayerState } from "./use-player";
export function Marked({
  text,
  ranges,
}: {
  text: string;
  ranges: [number, number][];
}) {
  const chars = Array.from(text);
  let end = 0;
  const parts: React.ReactNode[] = [];
  ranges.forEach(([from, to], index) => {
    parts.push(
      chars.slice(end, from).join(""),
      <mark key={index}>{chars.slice(from, to).join("")}</mark>,
    );
    end = to;
  });
  parts.push(chars.slice(end).join(""));
  return <>{parts}</>;
}
export function TranscriptPanel({
  id,
  timeline,
  player,
  initialSegment,
}: {
  id: string;
  timeline: TimelineEntry[];
  player: PlayerState;
  initialSegment: string | null;
}) {
  const [editing, setEditing] = useState<Segment | null>(null);
  const [query, setQuery] = useState("");
  const [speakerFilter, setSpeaker] = useState("");
  const speaker = player.follow ? "" : speakerFilter;
  const { follow, setFollow } = player;
  const [annotation, setAnnotation] = useState<{
    segment: Segment;
    start: number;
    end: number;
  } | null>(null);
  const [manualOffset, setManualOffset] = useState(0);
  const [hitCursor, setHitCursor] = useState(0);
  const active = locate(timeline, player.time);
  const position = active.segment ? timeline.indexOf(active.segment) : 0;
  const offset =
    follow && !speaker ? Math.floor(position / 40) * 40 : manualOffset;
  const transcript = useApi<TranscriptData>(
    `meetings/${id}/transcript?cursor=${offset}&speaker=${speaker}`.replace(
      /&speaker=$/,
      "",
    ),
  );
  const speakers = useApi<Speaker[]>(`meetings/${id}/speakers`);
  const results = useApi<TranscriptSearch>(
    `meetings/${id}/transcript/search?q=${encodeURIComponent(query || " ")}&cursor=${hitCursor}${speaker ? `&speaker=${speaker}` : ""}`,
    Boolean(query),
  );
  const scroll = useRef<HTMLDivElement>(null);
  const initialized = useRef<string | null>(null);
  useEffect(() => {
    if (initialSegment !== initialized.current && timeline.length) {
      initialized.current = initialSegment;
      const segment = timeline.find((s) => s.public_id === initialSegment);
      if (segment) player.seek(segment.start_ms);
    }
  }, [initialSegment, timeline, player]);
  useEffect(() => {
    if (follow && active.segment && scroll.current) {
      const row = scroll.current.querySelector<HTMLElement>(
        `[data-segment="${active.segment.public_id}"]`,
      );
      if (row)
        scroll.current.scrollTo({
          top: row.offsetTop - scroll.current.offsetTop - 70,
          behavior: "instant",
        });
    }
  }, [active.segment, follow, transcript.data]);
  function seek(time: number) {
    setSpeaker("");
    setFollow(true);
    player.seek(time);
  }
  return (
    <section className="transcript-panel" aria-label="Transcript">
      <div className="panel-heading">
        <h2>
          <TextCursorInput size={18} /> Transcript
        </h2>
        <button
          className={follow ? "small-button selected" : "small-button"}
          aria-pressed={follow}
          onClick={() => {
            setSpeaker("");
            setFollow(!follow);
          }}
        >
          Follow {follow ? "on" : "off"}
        </button>
      </div>
      <div className="transcript-tools">
        <div className="search-field">
          <Search size={16} />
          <input
            aria-label="Search transcript"
            placeholder="Search this transcript…"
            maxLength={200}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setHitCursor(0);
            }}
          />
          {query && (
            <button
              onClick={() => {
                setQuery("");
                setHitCursor(0);
              }}
            >
              Clear
            </button>
          )}
        </div>
        <select
          aria-label="Filter transcript speaker"
          value={speaker}
          onChange={(e) => {
            setSpeaker(e.target.value);
            setManualOffset(0);
            setHitCursor(0);
            setFollow(false);
          }}
        >
          <option value="">All speakers</option>
          {speakers.data?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.display_name}
            </option>
          ))}
        </select>
      </div>
      {query && (
        <div className="transcript-results">
          <p className="muted">
            {results.data
              ? `${results.data.total} matching turns`
              : "Searching…"}
          </p>
          <ErrorNotice error={results.error} />
          {results.data?.items.map((hit) => (
            <button
              className="search-hit"
              key={hit.segment_id}
              onClick={() => seek(hit.timestamp_ms)}
            >
              <strong>
                {hit.speaker_name} · {timestamp(hit.timestamp_ms)}
              </strong>
              <span>
                <Marked text={hit.snippet} ranges={hit.ranges} />
              </span>
            </button>
          ))}
          <div className="pagination">
            <button
              disabled={!hitCursor}
              onClick={() => setHitCursor(Math.max(0, hitCursor - 100))}
            >
              Previous results
            </button>
            <button
              disabled={!results.data?.next_cursor}
              onClick={() => setHitCursor(results.data?.next_cursor ?? 0)}
            >
              Next results
            </button>
          </div>
        </div>
      )}
      <div className="transcript-context">
        {active.gap
          ? "Gap in transcript · previous turn shown for context"
          : "Following transcript timing"}
        {!follow && " · Follow paused"}
      </div>
      <ErrorNotice error={transcript.error} />
      {transcript.isError && (
        <button onClick={() => transcript.refetch()}>Retry transcript</button>
      )}
      <div
        ref={scroll}
        className="transcript-scroll"
        tabIndex={0}
        aria-label="Transcript turns"
        onWheel={() => setFollow(false)}
        onTouchMove={() => setFollow(false)}
        onKeyDown={(e) => {
          if (
            [
              "ArrowDown",
              "ArrowUp",
              "PageDown",
              "PageUp",
              "Home",
              "End",
            ].includes(e.key)
          )
            setFollow(false);
        }}
      >
        {!transcript.data && <p>Loading transcript…</p>}
        {transcript.data?.items.map((segment) => (
          <article
            className={`transcript-turn ${active.segment?.public_id === segment.public_id ? "current" : ""}`}
            data-segment={segment.public_id}
            key={segment.public_id}
          >
            <Avatar name={segment.speaker_name} small />
            <div>
              <div className="turn-heading">
                <strong>{segment.speaker_name}</strong>
                <button
                  className="timestamp"
                  aria-label={`Seek to ${timestamp(segment.start_ms)}`}
                  onClick={() => seek(segment.start_ms)}
                >
                  {timestamp(segment.start_ms)}
                </button>
                {active.segment?.public_id === segment.public_id && (
                  <span className="turn-state">
                    {active.gap ? "Context" : "Current"}
                  </span>
                )}
              </div>
              <p
                onMouseUp={(e) => {
                  const range = selectedRange(e.currentTarget);
                  if (range) setAnnotation({ segment, ...range });
                }}
              >
                {highlightChunks(segment.text, segment.highlights ?? []).map(
                  (chunk, index) =>
                    chunk.color ? (
                      <mark className={`tag-${chunk.color}`} key={index}>
                        {chunk.text}
                      </mark>
                    ) : (
                      chunk.text
                    ),
                )}
              </p>
              <button
                className="source-link"
                onClick={() =>
                  setAnnotation({
                    segment,
                    start: 0,
                    end: Array.from(segment.text).length,
                  })
                }
              >
                Annotate turn
              </button>
              <button
                className="source-link"
                onClick={() => setEditing(segment)}
              >
                Edit turn
              </button>
            </div>
          </article>
        ))}
      </div>
      <div className="pagination">
        <span className="muted">
          Turns {offset + 1}–{offset + (transcript.data?.items.length ?? 0)}
        </span>
        <div>
          <button
            disabled={!offset}
            onClick={() => {
              setFollow(false);
              setManualOffset(Math.max(0, offset - 60));
            }}
          >
            Previous turns
          </button>
          <button
            disabled={!transcript.data?.has_more}
            onClick={() => {
              setFollow(false);
              setManualOffset(transcript.data?.next_cursor ?? 0);
            }}
          >
            Next turns
          </button>
        </div>
      </div>
      {annotation && (
        <AnnotationCreate
          id={id}
          segment={annotation.segment}
          selection={annotation}
          close={() => setAnnotation(null)}
        />
      )}
      {editing && (
        <SegmentEditor
          id={id}
          segment={editing}
          close={() => setEditing(null)}
        />
      )}
    </section>
  );
}
