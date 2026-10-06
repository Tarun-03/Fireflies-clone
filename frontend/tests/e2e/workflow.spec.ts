import { expect, test } from "@playwright/test";
test("one meeting completes the full notebook workflow", async ({ page }) => {
  test.setTimeout(90000);
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Search meeting titles" })
    .fill("standup");
  await expect(page.locator(".meeting-title")).toHaveCount(1);
  await page.locator(".meeting-title").click();
  await page
    .getByRole("textbox", { name: "Search transcript" })
    .fill("freshness");
  await page.locator(".search-hit").first().click();
  await page
    .getByRole("button", { name: "Create meeting", exact: true })
    .click();
  let dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Meeting title", { exact: true })
    .fill("Complete evaluation notebook");
  await dialog
    .getByLabel("Transcript", { exact: true })
    .fill(
      "Sam: I will verify the quasar pilot.\nLee: We decided to use the café room.",
    );
  await dialog
    .getByRole("button", { name: "Preview transcript", exact: true })
    .click();
  await dialog
    .getByRole("checkbox", {
      name: "I understand these timestamps are estimated.",
    })
    .check();
  await dialog
    .getByRole("button", { name: "Create meeting", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await page
    .getByRole("button", { name: "Edit turn", exact: true })
    .first()
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("textbox", { name: "Transcript text", exact: true })
    .fill("I will verify the quasar pilot checklist.");
  await dialog
    .getByRole("button", { name: "Save transcript", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await page
    .getByRole("button", { name: "Regenerate notes", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Regenerate", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page
    .getByRole("checkbox", {
      name: "Complete I will verify the quasar pilot checklist.",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("checkbox", {
      name: "Reopen I will verify the quasar pilot checklist.",
      exact: true,
    }),
  ).toBeChecked();
  await page
    .getByRole("button", { name: "Annotate turn", exact: true })
    .first()
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("combobox", { name: "Annotation type", exact: true })
    .selectOption("comments");
  await dialog
    .getByRole("textbox", { name: "Comment", exact: true })
    .fill("Verified source in the full workflow.");
  await dialog
    .getByRole("button", { name: "Add comment", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await page.keyboard.press("ControlOrMeta+k");
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("textbox", { name: "Search all meetings" })
    .fill("quasar");
  await dialog.locator(".global-search-hit").first().click();
  await page
    .getByRole("button", { name: "Meeting assistant", exact: true })
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("textbox", { name: "Ask a question" })
    .fill("What about quasar?");
  await dialog
    .getByRole("button", { name: "Ask meeting", exact: true })
    .click();
  await expect(dialog.locator(".chat-message.assistant")).toContainText(
    "checklist",
  );
  await dialog.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Export", exact: true }).click();
  const download = page.waitForEvent("download");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Download", exact: true })
    .click();
  expect((await download).suggestedFilename()).toBe("meeting-part-1-of-1.pdf");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close dialog" })
    .click();
  await page
    .getByRole("button", { name: "Actions for Complete evaluation notebook" })
    .click();
  await page.getByRole("menuitem", { name: "Delete meeting" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete meeting", exact: true })
    .click();
  await expect(page).toHaveURL("http://localhost:3000/");
  await page.reload();
  await expect(
    page.getByRole("link", {
      name: "Complete evaluation notebook",
      exact: true,
    }),
  ).toHaveCount(0);
});
