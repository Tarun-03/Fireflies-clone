"use client";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction } from "@/components/providers";
const schema = z.object({
  title: z.string().trim().min(1).max(200),
  speaker: z.string().trim().min(1).max(120),
  text: z.string().trim().min(1).max(10000),
  date: z.string().min(1),
  duration: z.coerce.number().min(1).max(360),
});
type Form = z.infer<typeof schema>;
export function CreateDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const action = useAction();
  const [key] = useState(() => crypto.randomUUID());
  const form = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "",
      speaker: "",
      text: "",
      date: new Date().toISOString().slice(0, 16),
      duration: 1,
    },
  });
  const submit = form.handleSubmit(async (values) => {
    await action
      .mutateAsync({
        path: "meetings",
        method: "POST",
        key,
        message: "Meeting created",
        body: {
          title: values.title,
          occurred_at: new Date(values.date).toISOString(),
          duration_ms: values.duration * 60000,
          source: "manual",
          participants: [{ display_name: values.speaker }],
          segments: [
            {
              speaker: values.speaker,
              start_ms: 0,
              end_ms: values.duration * 60000,
              text: values.text,
            },
          ],
        },
      })
      .then(
        () => {
          form.reset();
          onOpenChange(false);
        },
        () => {},
      );
  });
  return (
    <Dialog
      title="Create meeting"
      description="Add a timed speaker turn to your private workspace."
      open={open}
      onOpenChange={onOpenChange}
    >
      <form onSubmit={submit} className="form-stack">
        <label>
          Meeting title
          <input
            {...form.register("title")}
            placeholder="e.g. Product review"
            autoFocus
          />
        </label>
        <div className="form-grid">
          <label>
            Meeting date
            <input type="datetime-local" {...form.register("date")} />
          </label>
          <label>
            Duration (minutes)
            <input
              type="number"
              {...form.register("duration")}
              min="1"
              max="360"
            />
          </label>
        </div>
        <label>
          Speaker
          <input {...form.register("speaker")} placeholder="Speaker name" />
        </label>
        <label>
          Transcript
          <textarea
            rows={7}
            {...form.register("text")}
            placeholder="What was discussed?"
          />
        </label>
        {Object.values(form.formState.errors).map((error, index) => (
          <p role="alert" className="error-notice" key={index}>
            {error.message}
          </p>
        ))}
        <ErrorNotice error={action.error} />
        <div className="dialog-actions">
          <button type="button" onClick={() => onOpenChange(false)}>
            Cancel
          </button>
          <button className="primary" disabled={action.isPending}>
            {action.isPending ? "Creating…" : "Create meeting"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
