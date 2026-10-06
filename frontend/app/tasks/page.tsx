"use client";
import { useState } from "react";
import { CheckSquare } from "lucide-react";
import { useApi, useAllPages } from "@/components/providers";
import { ErrorNotice } from "@/components/dialog";
import { TaskRow } from "@/features/tasks/task-row";
import type { Page, Participant, Task } from "@/lib/types";
export default function TasksPage() {
  const [status, setStatus] = useState("");
  const [cursor, setCursor] = useState("");
  const people = useAllPages<Participant>("participants");
  const tasks = useApi<Page<Task>>(
    `action-items?limit=50${status ? `&status=${status}` : ""}${cursor ? `&cursor=${cursor}` : ""}`,
  );
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
          onChange={(e) => {
            setStatus(e.target.value);
            setCursor("");
          }}
        >
          <option value="">All tasks</option>
          <option value="open">Open</option>
          <option value="completed">Completed</option>
        </select>
      </div>
      <ErrorNotice error={tasks.error} />
      {tasks.isError && (
        <button onClick={() => tasks.refetch()}>Retry tasks</button>
      )}
      {tasks.isLoading ? (
        <p>Loading action items…</p>
      ) : tasks.data?.items.length === 0 ? (
        <div className="empty-state">
          <CheckSquare size={30} />
          <h2>Nothing to follow up on</h2>
          <p>Add action items inside a meeting notebook.</p>
        </div>
      ) : (
        <div className="task-list">
          {tasks.data?.items.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              people={people.data?.items ?? []}
              showMeeting
            />
          ))}
        </div>
      )}
      <div className="pagination">
        <span>{tasks.data?.items.length ?? 0} tasks on this page</span>
        <div>
          <button disabled={!cursor} onClick={() => setCursor("")}>
            First page
          </button>
          <button
            disabled={!tasks.data?.next_cursor}
            onClick={() => setCursor(tasks.data?.next_cursor ?? "")}
          >
            Next page
          </button>
        </div>
      </div>
    </div>
  );
}
