"use client";
import { useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction, useApi } from "@/components/providers";
import { timestamp } from "@/lib/time";
import type { ChatHistory, ChatResult, IntelligenceStatus } from "@/lib/types";
export function MeetingChat({
  id,
  seek,
}: {
  id: string;
  seek: (time: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState("extractive");
  const [consent, setConsent] = useState(false);
  const [cursor, setCursor] = useState(0);
  const [notice, setNotice] = useState("");
  const [clearing, setClearing] = useState(false);
  const request = useRef({ signature: "", key: "" });
  const controller = useRef<AbortController | null>(null);
  const history = useApi<ChatHistory>(
    `meetings/${id}/chat?cursor=${cursor}`,
    open,
  );
  const status = useApi<IntelligenceStatus>("intelligence", open);
  const action = useAction();
  async function submit() {
    const body = { question, mode, consent };
    const signature = JSON.stringify(body);
    if (signature !== request.current.signature)
      request.current = { signature, key: crypto.randomUUID() };
    controller.current = new AbortController();
    await action
      .mutateAsync({
        path: `meetings/${id}/chat`,
        method: "POST",
        body,
        version: history.data?.version,
        key: request.current.key,
        signal: controller.current.signal,
      })
      .then(
        ({ result }) => {
          setNotice((result as ChatResult).notice ?? "");
          setQuestion("");
          setCursor(0);
          request.current = { signature: "", key: "" };
        },
        () => {},
      );
  }
  return (
    <>
      <button
        className="icon-button"
        title="Ask about this meeting"
        aria-label="Meeting assistant"
        onClick={() => setOpen(true)}
      >
        <Sparkles size={18} />
      </button>
      <Dialog
        drawer
        open={open}
        onOpenChange={(value) => {
          setOpen(value);
          if (!value) controller.current?.abort();
        }}
        title="Meeting assistant"
        description="Answers and excerpts grounded in this meeting’s transcript."
      >
        <div className="form-stack">
          <label>
            Answer mode
            <select
              value={mode}
              disabled={action.isPending}
              onChange={(e) => setMode(e.target.value)}
            >
              <option value="extractive">Extractive mode</option>
              <option value="openai" disabled={!status.data?.available}>
                OpenAI{" "}
                {status.data?.available
                  ? `· ${status.data.model}`
                  : "— not configured"}
              </option>
            </select>
          </label>
          {mode === "openai" ? (
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              Send selected meeting evidence and recent chat to OpenAI
            </label>
          ) : (
            <p className="muted">
              Local transcript excerpts only. Generated reasoning is unavailable
              in extractive mode.
            </p>
          )}
          <div
            className="chat-history"
            aria-label="Chat history"
            aria-busy={history.isLoading || action.isPending}
          >
            {history.isLoading && <p role="status">Loading conversation…</p>}
            {history.data?.items.length === 0 && (
              <div className="chat-suggestions">
                <p>Start with a question about the conversation.</p>
                {[
                  "Summarize the meeting",
                  "What decisions were discussed?",
                  "What action items were mentioned?",
                ].map((q) => (
                  <button key={q} onClick={() => setQuestion(q)}>
                    {q}
                  </button>
                ))}
              </div>
            )}
            {history.data?.items.map((message) => (
              <article
                className={`chat-message ${message.role}`}
                key={message.id}
              >
                <strong>
                  {message.role === "user"
                    ? "You"
                    : message.provider === "openai"
                      ? "Assistant · OpenAI"
                      : "Transcript · Extractive"}
                </strong>
                <p>{message.content}</p>
                {message.source_revision !==
                  history.data.transcript_revision && (
                  <small className="muted">
                    Historical response · transcript has changed
                  </small>
                )}
                <div className="chat-citations">
                  {(message.citations ?? []).map((citation) => (
                    <button
                      key={citation.original_segment_public_id}
                      disabled={!citation.segment_id}
                      onClick={() => {
                        seek(citation.timestamp_ms);
                        setOpen(false);
                      }}
                    >
                      {timestamp(citation.timestamp_ms)}
                      {citation.segment_id ? " ↗" : " · source removed"}
                    </button>
                  ))}
                </div>
              </article>
            ))}
          </div>
          <div className="pagination">
            <button disabled={!cursor} onClick={() => setCursor(0)}>
              Latest
            </button>
            <button
              disabled={!history.data?.next_cursor}
              onClick={() => setCursor(history.data?.next_cursor ?? 0)}
            >
              Older messages
            </button>
          </div>
          <ErrorNotice error={action.error ?? history.error} />
          {action.error && (
            <button onClick={() => history.refetch()}>
              Refresh conversation, keep question
            </button>
          )}
          {notice && <p className="notice">{notice}</p>}
          <form
            className="form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              void submit();
            }}
          >
            <label>
              Ask a question
              <textarea
                maxLength={2000}
                required
                rows={3}
                value={question}
                disabled={action.isPending}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="What did we decide about the pilot?"
              />
            </label>
            <div className="dialog-actions">
              {action.isPending && (
                <button
                  type="button"
                  onClick={() => controller.current?.abort()}
                >
                  Cancel request
                </button>
              )}
              <button
                className="primary"
                disabled={
                  action.isPending ||
                  !question.trim() ||
                  !history.data ||
                  (mode === "openai" && !consent)
                }
              >
                {action.isPending ? "Finding evidence…" : "Ask meeting"}
              </button>
            </div>
          </form>
          {clearing ? (
            <div className="notice">
              <p>Delete all saved questions and answers for this meeting?</p>
              <button
                disabled={action.isPending}
                onClick={() =>
                  action
                    .mutateAsync({
                      path: `meetings/${id}/chat`,
                      method: "DELETE",
                      version: history.data?.version,
                      message: "Chat history cleared",
                    })
                    .then(
                      () => {
                        setClearing(false);
                        setCursor(0);
                      },
                      () => {},
                    )
                }
              >
                Confirm clear history
              </button>
              <button onClick={() => setClearing(false)}>Keep history</button>
            </div>
          ) : (
            <button
              className="small-button"
              disabled={!history.data?.items.length || action.isPending}
              onClick={() => setClearing(true)}
            >
              Clear history…
            </button>
          )}
        </div>
      </Dialog>
    </>
  );
}
