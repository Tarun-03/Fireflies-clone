"use client";
import { useRouter, usePathname } from "next/navigation";
import { MeetingPeople } from "./meeting-people";
import { api, ApiError } from "@/lib/api";
import { useState } from "react";
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction } from "@/components/providers";
import type { Meeting } from "@/lib/types";
export function MeetingMenu({ meeting }: { meeting: Meeting }) {
  const [mode, setMode] = useState<"edit" | "delete" | "people" | null>(null);
  const router = useRouter();
  const pathname = usePathname();
  const [date, setDate] = useState(meeting.occurred_at.slice(0, 16));
  const [duration, setDuration] = useState(meeting.duration_ms / 60000);
  const [description, setDescription] = useState(meeting.description ?? "");
  const [version, setVersion] = useState(meeting.version);
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
            <Dropdown.Item
              onSelect={() => {
                setVersion(meeting.version);
                setTitle(meeting.title);
                setDate(meeting.occurred_at.slice(0, 16));
                setDuration(meeting.duration_ms / 60000);
                setDescription(meeting.description ?? "");
                setMode("edit");
              }}
            >
              <Pencil size={15} />
              Edit meeting
            </Dropdown.Item>
            <Dropdown.Item onSelect={() => setMode("people")}>
              Attendees and tags
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
      {mode === "people" && (
        <MeetingPeople meeting={meeting} close={() => setMode(null)} />
      )}
      {mode && mode !== "people" && (
        <Dialog
          open
          onOpenChange={() => setMode(null)}
          title={mode === "edit" ? "Edit meeting" : "Delete meeting?"}
          description={
            mode === "delete"
              ? "This permanently removes the transcript, notes, tasks, annotations, and chat for this meeting."
              : "Update the meeting details. Dates in this editor use UTC."
          }
        >
          {mode === "edit" && (
            <div className="form-stack">
              <label>
                Meeting title
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  maxLength={200}
                />
              </label>
              <label>
                Meeting date (UTC)
                <input
                  type="datetime-local"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
              </label>
              <label>
                Duration (minutes)
                <input
                  type="number"
                  min={1 / 60}
                  max={360}
                  step="any"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                />
              </label>
              <label>
                Description
                <textarea
                  rows={3}
                  maxLength={4000}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </label>
            </div>
          )}
          <ErrorNotice error={action.error} />
          {action.error instanceof ApiError && action.error.status === 409 && (
            <button
              onClick={() =>
                api<Meeting>(`meetings/${meeting.id}`).then(
                  (latest) => setVersion(latest.version),
                  () => {},
                )
              }
            >
              Load latest version, keep draft
            </button>
          )}
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
                    version: mode === "delete" ? meeting.version : version,
                    body:
                      mode === "delete"
                        ? undefined
                        : {
                            title,
                            occurred_at: new Date(date + "Z").toISOString(),
                            duration_ms: Math.round(duration * 60000),
                            description,
                          },
                    message:
                      mode === "delete" ? "Meeting deleted" : "Meeting renamed",
                  })
                  .then(
                    () => {
                      setMode(null);
                      if (
                        mode === "delete" &&
                        pathname.startsWith("/meetings/")
                      )
                        router.push("/");
                    },
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
