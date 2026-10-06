"use client";
import { useState } from "react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction } from "@/components/providers";
import type { Soundbite } from "@/lib/types";
export function SoundbiteEditor({
  id,
  time,
  duration,
  item,
  close,
}: {
  id: string;
  time: number;
  duration: number;
  item?: Soundbite;
  close: () => void;
}) {
  const [title, setTitle] = useState(item?.title ?? "");
  const [start, setStart] = useState(
    (item?.start_ms ?? Math.min(time, duration - 1000)) / 1000,
  );
  const [end, setEnd] = useState(
    (item?.end_ms ?? Math.min(time + 30000, duration)) / 1000,
  );
  const [deleting, setDeleting] = useState(false);
  const action = useAction();
  return (
    <Dialog
      open
      onOpenChange={close}
      title={
        deleting
          ? "Delete soundbite?"
          : item
            ? "Edit soundbite"
            : "Save soundbite"
      }
      description="A named playback interval with timestamped text export. This does not create an audio clip."
    >
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          action
            .mutateAsync({
              path: `meetings/${id}/soundbites${item ? `/${item.id}` : ""}`,
              method: deleting ? "DELETE" : item ? "PATCH" : "POST",
              version: item?.version,
              body: deleting
                ? undefined
                : {
                    title,
                    start_ms: Math.round(start * 1000),
                    end_ms: Math.round(end * 1000),
                  },
              message: deleting ? "Soundbite deleted" : "Soundbite saved",
            })
            .then(close, () => {});
        }}
      >
        {!deleting && (
          <>
            <label>
              Soundbite name
              <input
                required
                maxLength={200}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <div className="form-grid">
              <label>
                Start seconds
                <input
                  type="number"
                  min={0}
                  max={duration / 1000}
                  step="0.001"
                  required
                  value={start}
                  onChange={(e) => setStart(Number(e.target.value))}
                />
              </label>
              <label>
                End seconds
                <input
                  type="number"
                  min={0}
                  max={duration / 1000}
                  step="0.001"
                  required
                  value={end}
                  onChange={(e) => setEnd(Number(e.target.value))}
                />
              </label>
            </div>
          </>
        )}
        <ErrorNotice error={action.error} />
        <div className="dialog-actions">
          <button type="button" onClick={close}>
            Cancel
          </button>
          {item && !deleting && (
            <button
              type="button"
              className="danger-text"
              onClick={() => setDeleting(true)}
            >
              Delete soundbite…
            </button>
          )}
          <button
            className={deleting ? "danger" : "primary"}
            disabled={
              action.isPending || (!deleting && (!title.trim() || end <= start))
            }
          >
            {deleting ? "Delete soundbite" : "Save soundbite"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
