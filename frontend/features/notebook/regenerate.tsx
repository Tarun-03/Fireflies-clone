"use client";
import { useRef, useState } from "react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction, useApi } from "@/components/providers";
import type { Summary, IntelligenceStatus } from "@/lib/types";
export function Regenerate({ id, summary }: { id: string; summary: Summary }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState("extractive");
  const [consent, setConsent] = useState(false);
  const [notice, setNotice] = useState("");
  const [key, setKey] = useState(() => crypto.randomUUID());
  const controller = useRef<AbortController | null>(null);
  const status = useApi<IntelligenceStatus>("intelligence");
  const action = useAction();
  return (
    <>
      <button
        className="small-button"
        onClick={() => {
          setKey(crypto.randomUUID());
          setOpen(true);
        }}
      >
        Regenerate notes
      </button>
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      <Dialog
        open={open}
        onOpenChange={(value) => {
          if (!value) controller.current?.abort();
          setOpen(value);
        }}
        title="Regenerate meeting notes"
        description="Manual, completed, and edited tasks and your personal notes are preserved."
      >
        <div className="form-stack">
          <label>
            Generation mode
            <select
              value={mode}
              onChange={(e) => {
                setMode(e.target.value);
                setKey(crypto.randomUUID());
              }}
              disabled={action.isPending}
            >
              <option value="extractive">Extractive — runs locally</option>
              <option value="openai" disabled={!status.data?.available}>
                OpenAI{" "}
                {status.data?.available
                  ? `· ${status.data.model}`
                  : "— not configured"}
              </option>
            </select>
          </label>
          <p className="muted">
            Extractive mode uses exact transcript sentences. OpenAI receives up
            to {status.data?.context_characters.toLocaleString() ?? "24,000"}{" "}
            characters of selected meeting evidence. No full-transcript coverage
            is claimed for long meetings.
          </p>
          {mode === "openai" && (
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              Send selected transcript text to OpenAI
            </label>
          )}
          <ErrorNotice error={action.error} />
          <div className="dialog-actions">
            <button
              onClick={() => {
                controller.current?.abort();
                setOpen(false);
              }}
            >
              Cancel
            </button>
            <button
              className="primary"
              disabled={action.isPending || (mode === "openai" && !consent)}
              onClick={() => {
                controller.current = new AbortController();
                action
                  .mutateAsync({
                    path: `meetings/${id}/summary/regenerate`,
                    method: "POST",
                    version: summary.version,
                    key,
                    signal: controller.current.signal,
                    body: { mode, consent },
                    message: "Meeting notes regenerated",
                  })
                  .then(
                    ({ result }) => {
                      setNotice(
                        (result as Summary).notice ??
                          (mode === "extractive"
                            ? "Generated from transcript · Extractive"
                            : "Generated using OpenAI from selected meeting evidence."),
                      );
                      setOpen(false);
                    },
                    () => {},
                  );
              }}
            >
              {action.isPending ? "Generating…" : "Regenerate"}
            </button>
          </div>
        </div>
      </Dialog>
    </>
  );
}
