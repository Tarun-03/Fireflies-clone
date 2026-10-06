"use client";
import { useState } from "react";
import { MessageSquare, Highlighter, Scissors, ListTree } from "lucide-react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction, useApi } from "@/components/providers";
import { timestamp } from "@/lib/time";
import { download } from "@/lib/download";
import type {
  Chapter,
  Comment,
  Highlight,
  Page,
  Soundbite,
  TimelineEntry,
} from "@/lib/types";
import type { PlayerState } from "./use-player";
import { colors } from "./annotation-create";
import { SoundbiteEditor } from "./soundbite-editor";
type Entry = Comment | Highlight;
export function NotebookTools({
  id,
  duration,
  timeline,
  player,
}: {
  id: string;
  duration: number;
  timeline: TimelineEntry[];
  player: PlayerState;
}) {
  const [panel, setPanel] = useState("");
  const [cursor, setCursor] = useState("");
  const [edit, setEdit] = useState<Entry | null>(null);
  const [clip, setClip] = useState<Soundbite | null | "new">(null);
  const [error, setError] = useState<Error | null>(null);
  const annotations = useApi<Page<Comment | Highlight | Soundbite>>(
    `meetings/${id}/${panel || "comments"}${cursor ? `?cursor=${cursor}` : ""}`,
    Boolean(panel) && panel !== "chapters",
  );
  const chapters = useApi<Chapter[]>(
    `meetings/${id}/chapters`,
    panel === "chapters",
  );
  function source(segmentId: string) {
    const segment = timeline.find((s) => s.public_id === segmentId);
    if (segment) {
      player.seek(segment.start_ms);
      setPanel("");
    }
  }
  return (
    <>
      <aside className="notebook-tools" aria-label="Notebook tools">
        {[
          ["comments", "Comments", MessageSquare],
          ["highlights", "Highlights", Highlighter],
          ["soundbites", "Soundbites", Scissors],
          ["chapters", "Outline", ListTree],
        ].map(([key, label, Icon]) => {
          const ToolIcon = Icon as typeof MessageSquare;
          return (
            <button
              className="icon-button"
              aria-label={label as string}
              title={label as string}
              key={key as string}
              onClick={() => {
                setPanel(key as string);
                setCursor("");
              }}
            >
              <ToolIcon size={18} />
            </button>
          );
        })}
      </aside>
      <Dialog
        drawer
        open={Boolean(panel)}
        onOpenChange={() => setPanel("")}
        title={
          panel === "chapters"
            ? "Outline"
            : panel === "comments"
              ? "Comments"
              : panel === "highlights"
                ? "Highlights"
                : "Soundbites"
        }
        description={
          panel === "soundbites"
            ? "Named intervals for playback and text excerpts."
            : "Review saved context and jump back to its source."
        }
      >
        <ErrorNotice error={error ?? annotations.error ?? chapters.error} />
        {panel === "soundbites" && (
          <button onClick={() => setClip("new")}>Save a soundbite</button>
        )}
        {panel === "chapters" ? (
          chapters.data?.map((chapter) => (
            <button
              className="chapter"
              key={chapter.id}
              onClick={() => {
                player.seek(chapter.start_ms);
                setPanel("");
              }}
            >
              <span className="timestamp">{timestamp(chapter.start_ms)}</span>
              <span>{chapter.title}</span>
            </button>
          ))
        ) : (
          <>
            <div className="annotation-list">
              {annotations.isLoading && <p>Loading annotations…</p>}
              {annotations.data?.items.length === 0 && (
                <p className="empty-state">
                  {panel === "soundbites"
                    ? "Save a named interval to revisit it."
                    : "Select transcript text or choose Annotate turn to save context."}
                </p>
              )}
              {annotations.data?.items.map((item) => (
                <article className="annotation-item" key={item.id}>
                  {"body" in item ? (
                    <p>{item.body}</p>
                  ) : "selected_text" in item ? (
                    <>
                      <blockquote
                        className={`highlight-quote tag-${item.color}`}
                      >
                        {item.selected_text}
                      </blockquote>
                      <p>{item.note}</p>
                    </>
                  ) : (
                    <>
                      <h3>{item.title}</h3>
                      <p>
                        {timestamp(item.start_ms)}–{timestamp(item.end_ms)}
                      </p>
                    </>
                  )}
                  <div className="annotation-actions">
                    {"segment_id" in item ? (
                      <>
                        <button onClick={() => source(item.segment_id)}>
                          Jump to source
                        </button>
                        <button onClick={() => setEdit(item)}>Edit</button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => {
                            void player.playRange(item.start_ms, item.end_ms);
                            setPanel("");
                          }}
                        >
                          Play interval
                        </button>
                        <button onClick={() => setClip(item)}>Edit</button>
                        <button
                          onClick={() =>
                            download(
                              `meetings/${id}/soundbites/${item.id}/export`,
                              "soundbite.txt",
                            ).catch((e) => setError(e as Error))
                          }
                        >
                          Export text
                        </button>
                      </>
                    )}
                  </div>
                </article>
              ))}
            </div>
            <div className="pagination">
              <button disabled={!cursor} onClick={() => setCursor("")}>
                First page
              </button>
              <button
                disabled={!annotations.data?.next_cursor}
                onClick={() => setCursor(annotations.data?.next_cursor ?? "")}
              >
                Next page
              </button>
            </div>
          </>
        )}
      </Dialog>
      {edit && (
        <AnnotationEditor id={id} item={edit} close={() => setEdit(null)} />
      )}{" "}
      {clip && (
        <SoundbiteEditor
          id={id}
          time={player.time}
          duration={duration}
          item={clip === "new" ? undefined : clip}
          close={() => setClip(null)}
        />
      )}
    </>
  );
}
function AnnotationEditor({
  id,
  item,
  close,
}: {
  id: string;
  item: Entry;
  close: () => void;
}) {
  const isComment = "body" in item;
  const [text, setText] = useState(isComment ? item.body : item.note);
  const [color, setColor] = useState(isComment ? "amber" : item.color);
  const [deleting, setDeleting] = useState(false);
  const action = useAction();
  return (
    <Dialog
      open
      onOpenChange={close}
      title={
        deleting
          ? "Delete annotation?"
          : isComment
            ? "Edit comment"
            : "Edit highlight"
      }
      description={
        deleting
          ? "This annotation will be permanently removed."
          : "Update your saved context."
      }
    >
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          action
            .mutateAsync({
              path: `meetings/${id}/${isComment ? "comments" : "highlights"}/${item.id}`,
              method: deleting ? "DELETE" : "PATCH",
              version: item.version,
              body: deleting
                ? undefined
                : isComment
                  ? { body: text }
                  : { note: text, color },
              message: deleting ? "Annotation deleted" : "Annotation updated",
            })
            .then(close, () => {});
        }}
      >
        {!deleting && (
          <>
            <label>
              {isComment ? "Comment" : "Highlight note"}
              <textarea
                rows={4}
                value={text}
                maxLength={4000}
                required={isComment}
                onChange={(e) => setText(e.target.value)}
              />
            </label>
            {!isComment && (
              <label>
                Highlight color
                <select
                  value={color}
                  onChange={(e) => setColor(e.target.value as typeof color)}
                >
                  {colors.map((c) => (
                    <option value={c} key={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </>
        )}
        <ErrorNotice error={action.error} />
        <div className="dialog-actions">
          <button type="button" onClick={close}>
            Cancel
          </button>
          {!deleting && (
            <button
              type="button"
              className="danger-text"
              onClick={() => setDeleting(true)}
            >
              Delete annotation…
            </button>
          )}
          <button
            className={deleting ? "danger" : "primary"}
            disabled={action.isPending}
          >
            {deleting ? "Delete annotation" : "Save annotation"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}
