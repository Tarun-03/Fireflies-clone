"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction, useApi } from "@/components/providers";
import { api } from "@/lib/api";
import { timestamp } from "@/lib/time";
import type {
  ImportPreview,
  Meeting,
  Page,
  SegmentInput,
  Tag,
} from "@/lib/types";
const schema = z.object({
  title: z.string().trim().min(1, "Enter a meeting title").max(200),
  date: z.string().min(1),
  attendees: z.string().max(12000),
});
type Form = z.infer<typeof schema>;
function localDate() {
  const date = new Date();
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}
export function CreateDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const action = useAction();
  const tags = useApi<Page<Tag>>("tags");
  const [mode, setMode] = useState("paste");
  const [text, setText] = useState("");
  const [file, setFile] = useState<{
    name: string;
    content: string;
    format: string;
  } | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [ack, setAck] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [turns, setTurns] = useState<SegmentInput[]>([
    { speaker: "", start_ms: 0, end_ms: 60000, text: "" },
  ]);
  const request = useRef({ signature: "", key: "" });
  const form = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", date: localDate(), attendees: "" },
  });
  function invalidate() {
    setPreview(null);
    setAck(false);
    setError(null);
  }
  function source() {
    return mode === "upload"
      ? {
          format: file?.format ?? "txt",
          filename: file?.name,
          content_base64: file?.content,
        }
      : { format: "txt", content: text };
  }
  async function loadFile(value: File | undefined) {
    invalidate();
    setFile(null);
    if (!value) return;
    try {
      if (value.size > 2 * 1024 * 1024)
        throw new Error("Choose a UTF-8 transcript of 2 MiB or less.");
      const bytes = new Uint8Array(await value.arrayBuffer());
      let binary = "";
      for (const byte of bytes) binary += String.fromCharCode(byte);
      setFile({
        name: value.name,
        format: value.name.split(".").pop()?.toLowerCase() ?? "",
        content: btoa(binary),
      });
    } catch (error) {
      setError(
        error instanceof Error ? error : new Error("Cannot read this file."),
      );
    }
  }
  async function parsePreview() {
    setPreviewing(true);
    setError(null);
    try {
      const result = await api<ImportPreview>("meetings/import/preview", {
        method: "POST",
        body: source(),
      });
      setPreview(result);
      if (result.title && !form.getValues("title"))
        form.setValue("title", result.title);
      if (result.occurred_at) {
        const date = new Date(result.occurred_at);
        date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
        form.setValue("date", date.toISOString().slice(0, 16));
      }
      if (result.participants.length && !form.getValues("attendees"))
        form.setValue(
          "attendees",
          result.participants
            .map((p) =>
              p.email ? `${p.display_name} <${p.email}>` : p.display_name,
            )
            .join("\n"),
        );
    } catch (error) {
      setError(
        error instanceof Error
          ? error
          : new Error("Could not preview this transcript."),
      );
    } finally {
      setPreviewing(false);
    }
  }
  const submit = async (values: Form) => {
    setError(null);
    const people = values.attendees
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((line) => {
        const match = line.match(/^(.*?)\s*<([^>]+)>$/);
        return match
          ? { display_name: match[1].trim(), email: match[2] }
          : { display_name: line };
      });
    const metadata = {
      title: values.title,
      occurred_at: new Date(values.date).toISOString(),
      participants: people,
      tag_ids: selectedTags,
    };
    const body =
      mode === "manual"
        ? {
            ...metadata,
            source: "manual",
            segments: turns,
            duration_ms: Math.max(...turns.map((t) => t.end_ms)),
          }
        : { ...source(), ...metadata, acknowledge_estimated: ack };
    const signature = JSON.stringify(body);
    if (request.current.signature !== signature)
      request.current = { signature, key: crypto.randomUUID() };
    await action
      .mutateAsync({
        path: mode === "manual" ? "meetings" : "meetings/import",
        method: "POST",
        key: request.current.key,
        body,
        message: "Meeting created",
      })
      .then(
        ({ result }) => {
          onOpenChange(false);
          router.push(`/meetings/${(result as Meeting).id}`);
          form.reset();
          setText("");
          setFile(null);
          setPreview(null);
        },
        () => {},
      );
  };
  return (
    <Dialog
      title="Create meeting"
      description="Bring your transcript into a private, searchable notebook."
      open={open}
      onOpenChange={onOpenChange}
    >
      <form
        className="form-stack"
        onSubmit={(e) => void form.handleSubmit(submit)(e)}
      >
        <div className="tabs">
          {[
            ["paste", "Paste transcript"],
            ["upload", "Upload transcript"],
            ["manual", "Manual entry"],
          ].map(([key, label]) => (
            <button
              type="button"
              className={mode === key ? "active" : ""}
              key={key}
              onClick={() => {
                setMode(key);
                invalidate();
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <label>
          Meeting title
          <input
            {...form.register("title")}
            placeholder="e.g. Product review"
            maxLength={200}
          />
        </label>
        <label>
          Meeting date ({Intl.DateTimeFormat().resolvedOptions().timeZone})
          <input type="datetime-local" {...form.register("date")} />
        </label>
        <label>
          Attendees — one per line
          <textarea
            rows={2}
            {...form.register("attendees")}
            placeholder={"Maya Chen <maya@example.com>\nJordan Lee"}
          />
        </label>
        <fieldset className="tag-picker">
          <legend>Tags</legend>
          {tags.data?.items.map((tag) => (
            <label key={tag.id}>
              <input
                type="checkbox"
                checked={selectedTags.includes(tag.id)}
                onChange={(e) =>
                  setSelectedTags(
                    e.target.checked
                      ? [...selectedTags, tag.id]
                      : selectedTags.filter((id) => id !== tag.id),
                  )
                }
              />
              {tag.name}
            </label>
          ))}
        </fieldset>
        {mode === "paste" && (
          <label>
            Transcript
            <textarea
              rows={7}
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                invalidate();
              }}
              placeholder={
                "[00:00] Maya: Let’s review the proposal.\n[00:30] Jordan: I will update the draft."
              }
            />
          </label>
        )}
        {mode === "upload" && (
          <>
            <label>
              Transcript file (.txt, .vtt, .json)
              <input
                type="file"
                accept=".txt,.vtt,.json"
                onChange={(e) => void loadFile(e.target.files?.[0])}
              />
            </label>
            <small>
              UTF-8, up to 2 MiB. Audio and video files are not supported.
            </small>
            <div className="example-links">
              Examples:{" "}
              {["txt", "vtt", "json"].map((format) => (
                <a
                  key={format}
                  href={`/examples/transcript.${format}`}
                  download
                >
                  {format.toUpperCase()}
                </a>
              ))}
            </div>
          </>
        )}
        {mode === "manual" && (
          <div className="manual-turns">
            {turns.map((turn, index) => (
              <fieldset className="manual-turn" key={index}>
                <legend>Turn {index + 1}</legend>
                <label>
                  Speaker
                  <input
                    value={turn.speaker}
                    maxLength={120}
                    required
                    onChange={(e) =>
                      setTurns(
                        turns.map((t, i) =>
                          i === index ? { ...t, speaker: e.target.value } : t,
                        ),
                      )
                    }
                  />
                </label>
                <div className="form-grid">
                  {["start_ms", "end_ms"].map((field) => (
                    <label key={field}>
                      {field === "start_ms" ? "Start seconds" : "End seconds"}
                      <input
                        type="number"
                        min={0}
                        max={21600}
                        step="0.001"
                        required
                        value={turn[field as "start_ms" | "end_ms"] / 1000}
                        onChange={(e) =>
                          setTurns(
                            turns.map((t, i) =>
                              i === index
                                ? {
                                    ...t,
                                    [field]: Math.round(
                                      Number(e.target.value) * 1000,
                                    ),
                                  }
                                : t,
                            ),
                          )
                        }
                      />
                    </label>
                  ))}
                </div>
                <label>
                  Text
                  <textarea
                    rows={3}
                    required
                    maxLength={10000}
                    value={turn.text}
                    onChange={(e) =>
                      setTurns(
                        turns.map((t, i) =>
                          i === index ? { ...t, text: e.target.value } : t,
                        ),
                      )
                    }
                  />
                </label>
                <button
                  type="button"
                  disabled={turns.length === 1}
                  onClick={() => setTurns(turns.filter((_, i) => i !== index))}
                >
                  Remove turn
                </button>
              </fieldset>
            ))}
            <button
              type="button"
              disabled={turns.length >= 3000}
              onClick={() =>
                setTurns([
                  ...turns,
                  {
                    speaker: "",
                    text: "",
                    start_ms: turns.at(-1)?.end_ms ?? 0,
                    end_ms: (turns.at(-1)?.end_ms ?? 0) + 60000,
                  },
                ])
              }
            >
              Add speaker turn
            </button>
          </div>
        )}
        {mode !== "manual" && (
          <button
            type="button"
            disabled={previewing || (mode === "upload" ? !file : !text.trim())}
            onClick={() => void parsePreview()}
          >
            {previewing ? "Checking transcript…" : "Preview transcript"}
          </button>
        )}
        {preview && (
          <section className="import-preview">
            <h3>
              {preview.segment_count} turns · {timestamp(preview.duration_ms)}
            </h3>
            {preview.warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
            {preview.segments.slice(0, 3).map((segment, i) => (
              <p key={i}>
                <strong>
                  {timestamp(segment.start_ms)} · {segment.speaker}
                </strong>
                <br />
                {segment.text.slice(0, 250)}
              </p>
            ))}
            {preview.estimated_timing && (
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={ack}
                  onChange={(e) => setAck(e.target.checked)}
                />
                I understand these timestamps are estimated.
              </label>
            )}
          </section>
        )}
        {Object.values(form.formState.errors).map((error, i) => (
          <p className="error-notice" role="alert" key={i}>
            {error.message}
          </p>
        ))}
        <ErrorNotice error={error ?? action.error} />
        <div className="dialog-actions">
          <button type="button" onClick={() => onOpenChange(false)}>
            Cancel
          </button>
          <button
            className="primary"
            disabled={
              action.isPending ||
              (mode !== "manual" &&
                (!preview || (preview.estimated_timing && !ack)))
            }
          >
            {action.isPending ? "Creating…" : "Create meeting"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
