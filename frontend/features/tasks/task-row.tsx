"use client";
import { useState } from "react";
import { Pencil } from "lucide-react";
import Link from "next/link";
import { useAction } from "@/components/providers";
import { ErrorNotice } from "@/components/dialog";
import type { Participant, Task } from "@/lib/types";
import { TaskEditor } from "./task-editor";
export function TaskRow({
  task,
  people,
  revision,
  seek,
  showMeeting = false,
}: {
  task: Task;
  people: Participant[];
  revision?: number;
  seek?: (id: string) => void;
  showMeeting?: boolean;
}) {
  const action = useAction();
  const [editing, setEditing] = useState(false);
  const owner = people.find((p) => p.id === task.assignee_participant_id);
  return (
    <div className="task-entry">
      <div className="task-row">
        <input
          type="checkbox"
          aria-label={`${task.status === "completed" ? "Reopen" : "Complete"} ${task.text}`}
          checked={task.status === "completed"}
          disabled={action.isPending}
          onChange={() =>
            action.mutate({
              path: `meetings/${task.meeting_id}/action-items/${task.id}`,
              method: "PATCH",
              version: task.version,
              body: {
                status: task.status === "completed" ? "open" : "completed",
              },
              message: "Task updated",
            })
          }
        />
        <span className={task.status === "completed" ? "completed" : ""}>
          {task.text}
          <small>
            {owner?.display_name ?? "Unassigned"} ·{" "}
            {task.due_date ? `Due ${task.due_date}` : "No due date"}
            {task.origin === "manual" ? " · Manual" : " · From transcript"}
            {revision &&
            task.source_revision &&
            task.source_revision !== revision
              ? " · Source changed"
              : ""}
          </small>
          {task.source_segment_id && seek && (
            <button
              className="source-link"
              onClick={() => seek(task.source_segment_id!)}
            >
              Source ↗
            </button>
          )}
          {showMeeting && (
            <Link className="source-link" href={`/meetings/${task.meeting_id}`}>
              View meeting
            </Link>
          )}
        </span>
        <button
          className="icon-button"
          aria-label={`Edit task: ${task.text}`}
          onClick={() => setEditing(true)}
        >
          <Pencil size={14} />
        </button>
      </div>
      <ErrorNotice error={action.error} />
      {editing && (
        <TaskEditor
          meetingId={task.meeting_id}
          task={task}
          close={() => setEditing(false)}
        />
      )}
    </div>
  );
}
