import { expect, test } from "@playwright/test";
import path from "node:path";
test("creates all import formats, edits transcript, retains conflicting draft, and deletes", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.goto("/");
  await expect(page.locator(".meeting-title")).toHaveCount(8);
  async function create(mode: string, title: string, file?: string) {
    await page
      .getByRole("button", { name: "Create meeting", exact: true })
      .click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: mode, exact: true }).click();
    await dialog.getByLabel("Meeting title", { exact: true }).fill(title);
    if (file)
      await dialog
        .getByLabel("Transcript file (.txt, .vtt, .json)", { exact: true })
        .setInputFiles(path.resolve("public/examples", file));
    else if (mode === "Paste transcript")
      await dialog
        .getByLabel("Transcript", { exact: true })
        .fill(
          "Sam: I will check the café 😀 launch checklist.\nLee: We decided to run the pilot on Friday.",
        );
    else {
      await dialog.getByLabel("Speaker", { exact: true }).fill("Sam");
      await dialog
        .getByLabel("Text", { exact: true })
        .fill("I will check the manual launch checklist.");
    }
    if (mode !== "Manual entry") {
      await dialog
        .getByRole("button", { name: "Preview transcript", exact: true })
        .click();
      await expect(dialog.locator(".import-preview")).toBeVisible();
      if (mode === "Paste transcript" || file?.endsWith("txt"))
        await dialog
          .getByRole("checkbox", {
            name: "I understand these timestamps are estimated.",
          })
          .check();
    }
    await dialog
      .getByRole("button", { name: "Create meeting", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: title, exact: true }),
    ).toBeVisible();
    await expect(dialog).toHaveCount(0);
  }
  await create("Paste transcript", "Browser paste import");
  await page
    .getByRole("button", { name: "Edit turn", exact: true })
    .first()
    .click();
  const edit = page.getByRole("dialog");
  await edit
    .getByRole("textbox", { name: "Transcript text", exact: true })
    .fill("Revised café 😀 evidence for the pilot.");
  await edit
    .getByRole("button", { name: "Save transcript", exact: true })
    .click();
  await expect(edit).toHaveCount(0);
  await expect(page.locator(".transcript-turn").first()).toContainText(
    "Revised café 😀 evidence",
  );
  await page.reload();
  await expect(page.locator(".transcript-turn").first()).toContainText(
    "Revised café 😀 evidence",
  );
  await page
    .getByRole("button", { name: "Edit turn", exact: true })
    .first()
    .click();
  await edit
    .getByRole("textbox", { name: "Transcript text", exact: true })
    .fill("My retained conflict draft");
  await page.evaluate(async () => {
    const id = location.pathname.split("/").pop();
    const token = await (await fetch("/api/session/csrf")).json();
    const segment = (
      await (await fetch(`/api/v1/meetings/${id}/transcript`)).json()
    ).items[0];
    const response = await fetch(
      `/api/v1/meetings/${id}/segments/${segment.public_id}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": token.csrf_token,
          "If-Match": String(segment.version),
        },
        body: JSON.stringify({
          text: "Concurrent update",
          start_ms: segment.start_ms,
          end_ms: segment.end_ms,
        }),
      },
    );
    if (!response.ok) throw new Error(await response.text());
  });
  await edit
    .getByRole("button", { name: "Save transcript", exact: true })
    .click();
  await expect(
    edit.getByRole("textbox", { name: "Transcript text", exact: true }),
  ).toHaveValue("My retained conflict draft");
  await expect(
    edit.getByRole("button", { name: "Load latest version, keep draft" }),
  ).toBeVisible();
  await edit
    .getByRole("button", { name: "Load latest version, keep draft" })
    .click();
  await expect(edit.getByRole("alert")).toContainText("Your draft is retained");
  await edit
    .getByRole("button", { name: "Save transcript", exact: true })
    .click();
  await expect(edit).toHaveCount(0);
  await create("Upload transcript", "Browser TXT import", "transcript.txt");
  await create("Upload transcript", "Browser VTT import", "transcript.vtt");
  await create("Upload transcript", "Browser JSON import", "transcript.json");
  await create("Manual entry", "Browser manual meeting");
  await page
    .getByRole("button", { name: "Actions for Browser manual meeting" })
    .click();
  await page.getByRole("menuitem", { name: "Delete meeting" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete meeting", exact: true })
    .click();
  await expect(page).toHaveURL("http://localhost:3000/");
  await page.reload();
  await expect(
    page.getByRole("link", { name: "Browser manual meeting", exact: true }),
  ).toHaveCount(0);
});
