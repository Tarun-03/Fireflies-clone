"use client";
import { useState } from "react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction } from "@/components/providers";
import type { Tag } from "@/lib/types";
export function TagDialog({
  tag,
  onClose,
}: {
  tag: Tag | "new";
  onClose: () => void;
}) {
  const [name, setName] = useState(tag === "new" ? "" : tag.name);
  const [color, setColor] = useState(tag === "new" ? "purple" : tag.color);
  const [deleting, setDeleting] = useState(false);
  const action = useAction();
  async function save() {
    await action
      .mutateAsync({
        path: tag === "new" ? "tags" : `tags/${tag.id}`,
        method: tag === "new" ? "POST" : "PATCH",
        version: tag === "new" ? undefined : tag.version,
        body: { name, color },
        message: "Tag saved",
      })
      .then(onClose, () => {});
  }
  return (
    <Dialog
      title={
        deleting ? "Delete tag?" : tag === "new" ? "Create tag" : "Edit tag"
      }
      open
      onOpenChange={onClose}
      description={
        deleting
          ? "This removes the tag from every meeting. Your meetings remain available."
          : "Organize your meetings with a reusable tag."
      }
    >
      {!deleting && (
        <div className="form-stack">
          <label>
            Name
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={60}
            />
          </label>
          <label>
            Color
            <select
              value={color}
              onChange={(event) => setColor(event.target.value)}
            >
              {["purple", "blue", "green", "amber", "rose", "gray"].map(
                (value) => (
                  <option key={value}>{value}</option>
                ),
              )}
            </select>
          </label>
        </div>
      )}
      <ErrorNotice error={action.error} />
      <div className="dialog-actions">
        {tag !== "new" && (
          <button
            className="danger-text"
            disabled={action.isPending}
            onClick={() =>
              deleting
                ? action
                    .mutateAsync({
                      path: `tags/${tag.id}`,
                      method: "DELETE",
                      version: tag.version,
                      message: "Tag deleted",
                    })
                    .then(onClose, () => {})
                : setDeleting(true)
            }
          >
            {deleting ? "Confirm delete" : "Delete tag"}
          </button>
        )}
        <button onClick={onClose}>Cancel</button>
        {!deleting && (
          <button
            className="primary"
            disabled={action.isPending || !name.trim()}
            onClick={save}
          >
            Save tag
          </button>
        )}
      </div>
    </Dialog>
  );
}
