"use client";
import Link from "next/link";
import { useState } from "react";
import { CheckSquare } from "lucide-react";
import { useAction, useApi } from "@/components/providers";
import { ErrorNotice } from "@/components/dialog";
import type { Page, Task } from "@/lib/types";
export default function TasksPage() {
  const [status, setStatus] = useState("");
  const tasks = useApi<Page<Task>>(
    `action-items${status ? `?status=${status}` : ""}`,
  );
  const action = useAction();
  return (
    <div className="library">
      <div className="page-heading">
        <div>
          <h1>Action items</h1>
          <p className="muted">Turn conversations into follow-through.</p>
        </div>
        <select
          aria-label="Task status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
        >
          <option value="">All tasks</option>
          <option value="open">Open</option>
          <option value="completed">Completed</option>
        </select>
      </div>
      <ErrorNotice error={tasks.error ?? action.error} />
      {tasks.isLoading ? (
        <p>Loading action items…</p>
      ) : !tasks.data?.items.length ? (
        <div className="empty-state">
          <CheckSquare size={30} />
          <h2>Nothing to follow up on</h2>
          <p>Action items from your meetings appear here.</p>
        </div>
      ) : (
        <div className="task-list">
          {tasks.data.items.map((task) => (
            <div className="task-row" key={task.id}>
              <input
                type="checkbox"
                aria-label={`Complete ${task.text}`}
                checked={task.status === "completed"}
                disabled={action.isPending}
                onChange={() =>
                  action.mutate({
                    path: `meetings/${task.meeting_id}/action-items/${task.id}`,
                    method: "PATCH",
                    version: task.version,
                    body: {
                      status:
                        task.status === "completed" ? "open" : "completed",
                    },
                  })
                }
              />
              <span className={task.status === "completed" ? "completed" : ""}>
                {task.text}
                <small>
                  {task.due_date ? `Due ${task.due_date}` : "No due date"} ·{" "}
                  {task.origin === "manual"
                    ? "Added manually"
                    : "From transcript"}
                </small>
              </span>
              <Link href={`/meetings/${task.meeting_id}`}>View meeting</Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
