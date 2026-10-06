"use client";
import { useState } from "react";
import { Dialog, ErrorNotice } from "@/components/dialog";
import { useAction, useApi, useAllPages } from "@/components/providers";
import type { Meeting, Page, Participant, Tag } from "@/lib/types";
export function MeetingPeople({
  meeting,
  close,
}: {
  meeting: Meeting;
  close: () => void;
}) {
  const people = useAllPages<Participant>("participants");
  const tags = useApi<Page<Tag>>("tags");
  const action = useAction();
  const [selected, setSelected] = useState(
    meeting.participants.map((p) => p.id),
  );
  const [chosenTags, setChosenTags] = useState(meeting.tags.map((t) => t.id));
  const [owner, setOwner] = useState("");
  return (
    <Dialog
      open
      onOpenChange={close}
      title="Attendees and tags"
      description="Speaker labels remain in the transcript when an attendee is removed."
    >
      <div className="form-stack">
        <fieldset className="tag-picker">
          <legend>Meeting attendees</legend>
          {people.data?.items.map((person) => (
            <label key={person.id}>
              <input
                type="checkbox"
                checked={selected.includes(person.id)}
                onChange={(e) =>
                  setSelected(
                    e.target.checked
                      ? [...selected, person.id]
                      : selected.filter((id) => id !== person.id),
                  )
                }
              />
              {person.display_name}
            </label>
          ))}
        </fieldset>
        <label>
          Tasks owned by removed attendees
          <select value={owner} onChange={(e) => setOwner(e.target.value)}>
            <option value="">Unassign their tasks</option>
            {people.data?.items
              .filter((p) => selected.includes(p.id))
              .map((p) => (
                <option key={p.id} value={p.id}>
                  Reassign to {p.display_name}
                </option>
              ))}
          </select>
        </label>
        <button
          disabled={action.isPending}
          onClick={() =>
            action.mutate({
              path: `meetings/${meeting.id}/participants`,
              method: "PUT",
              version: meeting.version,
              body: {
                participant_ids: selected,
                removed_task_action: owner ? "reassign" : "unassign",
                reassign_to: owner || null,
              },
              message: "Attendees updated",
            })
          }
        >
          Save attendees
        </button>
        <fieldset className="tag-picker">
          <legend>Meeting tags</legend>
          {tags.data?.items.map((tag) => (
            <label key={tag.id}>
              <input
                type="checkbox"
                checked={chosenTags.includes(tag.id)}
                onChange={(e) =>
                  setChosenTags(
                    e.target.checked
                      ? [...chosenTags, tag.id]
                      : chosenTags.filter((id) => id !== tag.id),
                  )
                }
              />
              {tag.name}
            </label>
          ))}
        </fieldset>
        <button
          disabled={action.isPending}
          onClick={() =>
            action.mutate({
              path: `meetings/${meeting.id}/tags`,
              method: "PUT",
              version: meeting.version,
              body: { tag_ids: chosenTags },
              message: "Tags updated",
            })
          }
        >
          Save tags
        </button>
        <ErrorNotice error={action.error} />
        <div className="dialog-actions">
          <button onClick={close}>Done</button>
        </div>
      </div>
    </Dialog>
  );
}
