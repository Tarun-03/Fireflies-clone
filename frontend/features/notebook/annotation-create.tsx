"use client";
import { useState } from "react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction } from "@/components/providers";
import type { Segment } from "@/lib/types";
export const colors = ["amber", "purple", "blue", "green", "rose"] as const;
export function AnnotationCreate({
  id,
  segment,
  selection,
  close,
}: {
  id: string;
  segment: Segment;
  selection: { start: number; end: number };
  close: () => void;
}) {
  const [kind, setKind] = useState("highlights");
  const [body, setBody] = useState("");
  const [color, setColor] = useState("amber");
  const [start, setStart] = useState(selection.start);
  const [end, setEnd] = useState(selection.end);
  const action = useAction();
  const chars = Array.from(segment.text);
  const selected = chars.slice(start, end).join("");
  return (
    <Dialog
      open
      onOpenChange={close}
      title="Annotate transcript"
      description="Annotations stay in your private workspace and link to this transcript turn."
    >
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          action
            .mutateAsync({
              path: `meetings/${id}/${kind}`,
              method: "POST",
              body: {
                segment_id: segment.public_id,
                segment_version: segment.version,
                ...(kind === "comments"
                  ? { body }
                  : {
                      start_offset: start,
                      end_offset: end,
                      selected_text: selected,
                      note: body,
                      color,
                    }),
              },
              message:
                kind === "comments" ? "Comment added" : "Highlight saved",
            })
            .then(close, () => {});
        }}
      >
        <label>
          Annotation type
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="highlights">Highlight / bookmark</option>
            <option value="comments">Comment</option>
          </select>
        </label>
        {kind === "highlights" && (
          <>
            <div className="form-grid">
              <label>
                Start character
                <input
                  type="number"
                  min={0}
                  max={chars.length - 1}
                  value={start}
                  onChange={(e) => setStart(Number(e.target.value))}
                />
              </label>
              <label>
                End character
                <input
                  type="number"
                  min={1}
                  max={chars.length}
                  value={end}
                  onChange={(e) => setEnd(Number(e.target.value))}
                />
              </label>
            </div>
            <small>
              Character positions count Unicode characters, including emoji,
              from zero. End is exclusive.
            </small>
            <blockquote className={`highlight-quote tag-${color}`}>
              {selected}
            </blockquote>
            <label>
              Highlight color
              <select value={color} onChange={(e) => setColor(e.target.value)}>
                {colors.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
        <label>
          {kind === "comments" ? "Comment" : "Highlight note (optional)"}
          <textarea
            rows={4}
            maxLength={4000}
            required={kind === "comments"}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
        </label>
        <ErrorNotice error={action.error} />
        <div className="dialog-actions">
          <button type="button" onClick={close}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={
              action.isPending || (kind === "highlights" && end <= start)
            }
          >
            {action.isPending
              ? "Saving…"
              : kind === "comments"
                ? "Add comment"
                : "Save highlight"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
