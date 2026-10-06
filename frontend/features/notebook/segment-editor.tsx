"use client";
import { useState } from "react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction, useApi } from "@/components/providers";
import { api, ApiError } from "@/lib/api";
import type { Segment, SegmentImpact, Speaker, Transcript } from "@/lib/types";
export function SegmentEditor({
  id,
  segment,
  close,
}: {
  id: string;
  segment: Segment;
  close: () => void;
}) {
  const [text, setText] = useState(segment.text);
  const [start, setStart] = useState(segment.start_ms / 1000);
  const [end, setEnd] = useState(segment.end_ms / 1000);
  const [version, setVersion] = useState(segment.version);
  const [ack, setAck] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const action = useAction();
  const impact = useApi<SegmentImpact>(
    `meetings/${id}/segments/${segment.public_id}/impact`,
  );
  const speakers = useApi<Speaker[]>(`meetings/${id}/speakers`);
  const speaker = speakers.data?.find((s) => s.id === segment.speaker_id);
  async function reloadVersion() {
    try {
      const page = await api<Transcript>(
        `meetings/${id}/transcript/window?segment_id=${segment.public_id}`,
      );
      const latest = page.items.find((s) => s.public_id === segment.public_id);
      if (latest) {
        setVersion(latest.version);
        setError(
          new Error(
            `Loaded version ${latest.version}. Your draft is retained. Review it before saving over the latest turn.`,
          ),
        );
      }
    } catch (e) {
      setError(e as Error);
    }
  }
  return (
    <Dialog
      open
      onOpenChange={close}
      title={deleting ? "Delete transcript turn?" : "Edit transcript turn"}
      description="Transcript changes mark generated notes and tasks stale. Saved chat excerpts remain historical snapshots."
    >
      <div className="form-stack">
        {speaker && !deleting && (
          <SpeakerEditor key={speaker.version} id={id} speaker={speaker} />
        )}
        {!deleting && (
          <>
            <div className="form-grid">
              <label>
                Start seconds
                <input
                  type="number"
                  min={0}
                  step="0.001"
                  value={start}
                  onChange={(e) => setStart(Number(e.target.value))}
                />
              </label>
              <label>
                End seconds
                <input
                  type="number"
                  min={0}
                  step="0.001"
                  value={end}
                  onChange={(e) => setEnd(Number(e.target.value))}
                />
              </label>
            </div>
            <label>
              Transcript text
              <textarea
                rows={7}
                maxLength={10000}
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </label>
          </>
        )}
        <p className="muted">
          This turn has {impact.data?.highlights ?? "…"} highlights,{" "}
          {impact.data?.comments ?? "…"} comments, and{" "}
          {impact.data?.citations ?? "…"} chat citations.{" "}
          {deleting
            ? "Deleting removes comments and highlights and detaches source links."
            : "Changing the text removes highlights and detaches live chat citations; comments remain attached."}
        </p>
        {!!impact.data?.highlights && text !== segment.text && !deleting && (
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
            />
            Remove affected highlights when saving
          </label>
        )}
        <ErrorNotice error={error ?? action.error} />
        {action.error instanceof ApiError && action.error.status === 409 && (
          <button onClick={() => void reloadVersion()}>
            Load latest version, keep draft
          </button>
        )}
        <div className="dialog-actions">
          <button onClick={close}>Cancel</button>
          {!deleting && (
            <button className="danger-text" onClick={() => setDeleting(true)}>
              Delete turn…
            </button>
          )}
          <button
            className={deleting ? "danger" : "primary"}
            disabled={
              action.isPending || !text.trim() || (!deleting && end <= start)
            }
            onClick={() =>
              action
                .mutateAsync({
                  path: `meetings/${id}/segments/${segment.public_id}`,
                  method: deleting ? "DELETE" : "PATCH",
                  version,
                  body: deleting
                    ? undefined
                    : {
                        text,
                        start_ms: Math.round(start * 1000),
                        end_ms: Math.round(end * 1000),
                        remove_affected_highlights: ack,
                      },
                  message: deleting
                    ? "Transcript turn deleted"
                    : "Transcript updated",
                })
                .then(close, () => {})
            }
          >
            {action.isPending
              ? "Saving…"
              : deleting
                ? "Delete turn"
                : "Save transcript"}
          </button>
        </div>
      </div>
    </Dialog>
  );
}
function SpeakerEditor({ id, speaker }: { id: string; speaker: Speaker }) {
  const [name, setName] = useState(speaker.display_name);
  const action = useAction();
  return (
    <div className="form-stack">
      <label>
        Speaker name (all their turns)
        <input
          maxLength={120}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <button
        disabled={
          !name.trim() || name === speaker.display_name || action.isPending
        }
        onClick={() =>
          action.mutate({
            path: `meetings/${id}/speakers/${speaker.id}`,
            method: "PATCH",
            version: speaker.version,
            body: {
              display_name: name,
              participant_id: speaker.participant_id,
            },
            message: "Speaker corrected",
          })
        }
      >
        Save speaker name
      </button>
      <ErrorNotice error={action.error} />
    </div>
  );
}
