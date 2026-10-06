"use client";
import { useState } from "react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction, useApi } from "@/components/providers";
import { api, ApiError } from "@/lib/api";
import type { Meeting, Page, Task } from "@/lib/types";
export function TaskEditor({
  meetingId,
  task,
  close,
}: {
  meetingId: string;
  task?: Task;
  close: () => void;
}) {
  const meeting = useApi<Meeting>(`meetings/${meetingId}`);
  const action = useAction();
  const [text, setText] = useState(task?.text ?? "");
  const [owner, setOwner] = useState(task?.assignee_participant_id ?? "");
  const [date, setDate] = useState(task?.due_date ?? "");
  const [version, setVersion] = useState(task?.version);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState("");
  async function latest() {
    try {
      const page = await api<Page<Task>>(`meetings/${meetingId}/action-items`);
      const current = page.items.find((t) => t.id === task?.id);
      if (!current) throw new Error("This task no longer exists.");
      setVersion(current.version);
      setNotice(
        "Latest version loaded. Review your retained draft before saving.",
      );
    } catch (e) {
      setNotice((e as Error).message);
    }
  }
  return (
    <Dialog
      open
      onOpenChange={close}
      title={
        deleting
          ? "Delete action item?"
          : task
            ? "Edit action item"
            : "Add action item"
      }
      description={
        deleting
          ? "This permanently removes the action item."
          : "Give the next step a clear owner and due date when known."
      }
    >
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          action
            .mutateAsync({
              path: `meetings/${meetingId}/action-items${task ? `/${task.id}` : ""}`,
              method: deleting ? "DELETE" : task ? "PATCH" : "POST",
              version,
              body: deleting
                ? undefined
                : {
                    text,
                    assignee_participant_id: owner || null,
                    due_date: date || null,
                  },
              message: deleting ? "Task deleted" : "Task saved",
            })
            .then(close, () => {});
        }}
      >
        {!deleting && (
          <>
            <label>
              Action item
              <textarea
                rows={3}
                maxLength={2000}
                required
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </label>
            <div className="form-grid">
              <label>
                Owner
                <select
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                >
                  <option value="">Unassigned</option>
                  {meeting.data?.participants.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Due date
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
              </label>
            </div>
          </>
        )}
        <ErrorNotice error={action.error} />
        {notice && <p role="status">{notice}</p>}
        {action.error instanceof ApiError && action.error.status === 409 && (
          <button type="button" onClick={() => void latest()}>
            Load latest version, keep draft
          </button>
        )}
        <div className="dialog-actions">
          <button type="button" onClick={close}>
            Cancel
          </button>
          {task && !deleting && (
            <button
              type="button"
              className="danger-text"
              onClick={() => setDeleting(true)}
            >
              Delete task…
            </button>
          )}
          <button
            className={deleting ? "danger" : "primary"}
            disabled={action.isPending || !text.trim()}
          >
            {action.isPending
              ? "Saving…"
              : deleting
                ? "Delete task"
                : "Save task"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
