"use client";
import { useState } from "react";
import { FileText, ListTree, Sparkles } from "lucide-react";
import { useAction, useApi } from "@/components/providers";
import { ErrorNotice } from "@/components/dialog";
import { MeetingTasks } from "@/features/tasks/meeting-tasks";
import { Regenerate } from "./regenerate";
import { api } from "@/lib/api";
import { timestamp } from "@/lib/time";
import type { Chapter, Summary, TimelineEntry } from "@/lib/types";
export function NotesPanel({
  id,
  seek,
  timeline,
}: {
  id: string;
  seek: (time: number) => void;
  timeline: TimelineEntry[];
}) {
  const summary = useApi<Summary>(`meetings/${id}/summary`);
  const chapters = useApi<Chapter[]>(`meetings/${id}/chapters`);
  function source(segment: string | null) {
    const target = timeline.find((s) => s.public_id === segment);
    if (target) seek(target.start_ms);
  }
  return (
    <section className="notes-panel" aria-label="Meeting notes">
      <div className="panel-heading">
        <h2>
          <Sparkles size={18} /> Meeting notes
        </h2>
        <span className="subtle-badge">
          {summary.data?.provider === "openai"
            ? "AI generated"
            : "Extractive summary"}
        </span>
      </div>
      <div className="notes-scroll">
        <ErrorNotice error={summary.error} />
        {summary.isError && (
          <button onClick={() => summary.refetch()}>Retry summary</button>
        )}
        {summary.data && (
          <>
            <section className="note-section">
              <h3>Overview</h3>
              {summary.data.stale && (
                <p className="notice">
                  Transcript changed. This summary needs regeneration.
                </p>
              )}
              <p>{summary.data.overview}</p>
              <Regenerate id={id} summary={summary.data} />
              <p className="provenance">
                {summary.data.provider} · transcript revision{" "}
                {summary.data.source_revision}
              </p>
            </section>
            {["key_point", "decision"].map((kind) => (
              <section className="note-section" key={kind}>
                <h3>{kind === "decision" ? "Decisions" : "Key points"}</h3>
                <ul className="summary-points">
                  {summary
                    .data!.points.filter((point) => point.kind === kind)
                    .map((point) => (
                      <li key={point.id}>
                        {point.text}
                        {point.source_segment_id && (
                          <button
                            className="source-link"
                            onClick={() => source(point.source_segment_id)}
                          >
                            Source ↗
                          </button>
                        )}
                      </li>
                    ))}
                </ul>
              </section>
            ))}
          </>
        )}
        <MeetingTasks id={id} seek={source} />
        <section className="note-section">
          <h3>
            <ListTree size={16} /> Outline
          </h3>
          {chapters.data?.map((chapter) => (
            <button
              className="chapter"
              key={chapter.id}
              onClick={() => seek(chapter.start_ms)}
            >
              <span className="timestamp">{timestamp(chapter.start_ms)}</span>
              <span>
                <strong>{chapter.title}</strong>
                <small>{chapter.description}</small>
              </span>
            </button>
          ))}
        </section>
        {summary.data && (
          <NotesEditor key={id} id={id} summary={summary.data} />
        )}
      </div>
    </section>
  );
}
function NotesEditor({ id, summary }: { id: string; summary: Summary }) {
  const [notes, setNotes] = useState(summary.notes);
  const [baseline, setBaseline] = useState(summary);
  const [reloadError, setReloadError] = useState<Error | null>(null);
  const action = useAction();
  return (
    <form
      className="note-section"
      onSubmit={(e) => {
        e.preventDefault();
        action
          .mutateAsync({
            path: `meetings/${id}/summary`,
            method: "PATCH",
            version: baseline.version,
            body: { notes },
            message: "Notes saved",
          })
          .then(
            ({ result }) => setBaseline(result as Summary),
            () => {},
          );
      }}
    >
      <h3>
        <FileText size={16} /> Personal notes
      </h3>
      <label className="sr-only" htmlFor="personal-notes">
        Personal notes
      </label>
      <textarea
        id="personal-notes"
        maxLength={20000}
        rows={5}
        placeholder="Add context, thoughts, or next steps…"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <ErrorNotice error={reloadError ?? action.error} />
      {action.error && (
        <button
          type="button"
          onClick={() =>
            api<Summary>(`meetings/${id}/summary`).then(
              (latest) => {
                setBaseline(latest);
                setReloadError(null);
              },
              (error) => setReloadError(error as Error),
            )
          }
        >
          Use latest version, keep draft
        </button>
      )}
      <button disabled={action.isPending || notes === baseline.notes}>
        {action.isPending ? "Saving…" : "Save notes"}
      </button>
    </form>
  );
}
