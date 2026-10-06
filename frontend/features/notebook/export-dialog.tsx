"use client";
import { useState } from "react";
import { Download } from "lucide-react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useApi } from "@/components/providers";
import { download } from "@/lib/download";
import type { ExportManifest } from "@/lib/types";
export function ExportDialog({ id }: { id: string }) {
  const [open, setOpen] = useState(false);
  const [format, setFormat] = useState("pdf");
  const [section, setSection] = useState("all");
  const [times, setTimes] = useState(true);
  const [speakers, setSpeakers] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [done, setDone] = useState<number[]>([]);
  const query = new URLSearchParams({
    section,
    timestamps: String(times),
    speaker_names: String(speakers),
  });
  const manifest = useApi<ExportManifest>(
    `meetings/${id}/export/manifest?${query}`,
    open,
  );
  return (
    <>
      <button className="small-button" onClick={() => setOpen(true)}>
        <Download size={14} /> Export
      </button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Export meeting"
        description="Download private copies of the meeting content."
      >
        <div className="form-stack">
          <div className="form-grid">
            <label>
              Format
              <select
                value={format}
                onChange={(e) => {
                  setFormat(e.target.value);
                  setDone([]);
                }}
              >
                <option value="pdf">PDF document</option>
                <option value="md">Markdown</option>
                <option value="txt">Plain text</option>
              </select>
            </label>
            <label>
              Content
              <select
                value={section}
                onChange={(e) => {
                  setSection(e.target.value);
                  setDone([]);
                }}
              >
                <option value="all">Complete notebook</option>
                <option value="transcript">Transcript only</option>
                <option value="summary">Summary and notes</option>
                <option value="tasks">Action items</option>
              </select>
            </label>
          </div>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={times}
              onChange={(e) => {
                setTimes(e.target.checked);
                setDone([]);
              }}
            />
            Include timestamps
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={speakers}
              onChange={(e) => {
                setSpeakers(e.target.checked);
                setDone([]);
              }}
            />
            Include speaker names
          </label>
          <p className="muted">{manifest.data?.note ?? "Preparing export…"}</p>
          <ErrorNotice error={error ?? manifest.error} />
          {manifest.data && (
            <div className="export-parts">
              {Array.from({ length: manifest.data.parts }, (_, i) => i + 1).map(
                (part) => (
                  <button
                    className="primary"
                    key={part}
                    disabled={busy !== null}
                    onClick={async () => {
                      setBusy(part);
                      setError(null);
                      try {
                        await download(
                          `meetings/${id}/export?${query}&format=${format}&part=${part}`,
                          `meeting-part-${part}-of-${manifest.data.parts}.${format}`,
                        );
                        setDone([...done, part]);
                      } catch (e) {
                        setError(e as Error);
                      } finally {
                        setBusy(null);
                      }
                    }}
                  >
                    {busy === part
                      ? "Preparing download…"
                      : `${done.includes(part) ? "Download again" : "Download"}${manifest.data.parts > 1 ? ` part ${part} of ${manifest.data.parts}` : ""}`}
                  </button>
                ),
              )}
            </div>
          )}
        </div>
      </Dialog>
    </>
  );
}
