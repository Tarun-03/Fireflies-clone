"use client";
import { useState } from "react";
import { CheckSquare } from "lucide-react";
import { useApi } from "@/components/providers";
import { ErrorNotice } from "@/components/dialog";
import type { Meeting, Page, Task } from "@/lib/types";
import { TaskRow } from "./task-row";
import { TaskEditor } from "./task-editor";
export function MeetingTasks({
  id,
  seek,
}: {
  id: string;
  seek: (id: string) => void;
}) {
  const meeting = useApi<Meeting>(`meetings/${id}`);
  const tasks = useApi<Page<Task>>(`meetings/${id}/action-items`);
  const [adding, setAdding] = useState(false);
  return (
    <section className="note-section">
      <h3>
        <CheckSquare size={16} />
        Action items{" "}
        <span className="count">
          {tasks.data?.items.filter((t) => t.status === "completed").length ??
            0}
          /{tasks.data?.items.length ?? 0}
        </span>
      </h3>
      <ErrorNotice error={tasks.error} />
      {tasks.data?.items.map((task) => (
        <TaskRow
          task={task}
          people={meeting.data?.participants ?? []}
          revision={meeting.data?.transcript_revision}
          seek={seek}
          key={task.id}
        />
      ))}
      {tasks.data?.items.length === 0 && (
        <p className="muted">No action items yet. Add the next step.</p>
      )}
      <button className="small-button" onClick={() => setAdding(true)}>
        Add action item
      </button>
      {adding && <TaskEditor meetingId={id} close={() => setAdding(false)} />}
    </section>
  );
}
