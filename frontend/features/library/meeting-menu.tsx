"use client";
import { useState } from "react";
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction } from "@/components/providers";
import type { Meeting } from "@/lib/types";
export function MeetingMenu({ meeting }: { meeting: Meeting }) {
  const [mode, setMode] = useState<"edit" | "delete" | null>(null);
  const [title, setTitle] = useState(meeting.title);
  const action = useAction();
  return (
    <>
      <Dropdown.Root>
        <Dropdown.Trigger
          className="icon-button"
          aria-label={`Actions for ${meeting.title}`}
        >
          <MoreHorizontal size={18} />
        </Dropdown.Trigger>
        <Dropdown.Portal>
          <Dropdown.Content className="dropdown" align="end">
            <Dropdown.Item onSelect={() => setMode("edit")}>
              <Pencil size={15} />
              Rename meeting
            </Dropdown.Item>
            <Dropdown.Item
              className="danger-text"
              onSelect={() => setMode("delete")}
            >
              <Trash2 size={15} />
              Delete meeting
            </Dropdown.Item>
          </Dropdown.Content>
        </Dropdown.Portal>
      </Dropdown.Root>
      {mode && (
        <Dialog
          open
          onOpenChange={() => setMode(null)}
          title={mode === "edit" ? "Rename meeting" : "Delete meeting?"}
          description={
            mode === "delete"
              ? "This permanently removes the transcript, notes, tasks, annotations, and chat for this meeting."
              : "Give this conversation a useful name."
          }
        >
          {mode === "edit" && (
            <label className="form-stack">
              Meeting title
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={200}
              />
            </label>
          )}
          <ErrorNotice error={action.error} />
          <div className="dialog-actions">
            <button onClick={() => setMode(null)}>Cancel</button>
            <button
              className={mode === "delete" ? "danger" : "primary"}
              disabled={action.isPending || !title.trim()}
              onClick={() =>
                action
                  .mutateAsync({
                    path: `meetings/${meeting.id}`,
                    method: mode === "delete" ? "DELETE" : "PATCH",
                    version: meeting.version,
                    body: mode === "delete" ? undefined : { title },
                    message:
                      mode === "delete" ? "Meeting deleted" : "Meeting renamed",
                  })
                  .then(
                    () => setMode(null),
                    () => {},
                  )
              }
            >
              {action.isPending
                ? "Saving…"
                : mode === "delete"
                  ? "Delete meeting"
                  : "Save changes"}
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}
