import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("comments, highlights, and bounded soundbites persist and export", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator(".meeting-title").nth(1).click();
  await page
    .getByRole("button", { name: "Annotate turn", exact: true })
    .first()
    .click();
  let dialog = page.getByRole("dialog");
  await dialog.getByLabel("Start character", { exact: true }).fill("0");
  await dialog.getByLabel("End character", { exact: true }).fill("5");
  await dialog
    .getByLabel("Highlight note (optional)", { exact: true })
    .fill("Revisit the first phrase");
  await dialog
    .getByRole("button", { name: "Save highlight", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await expect(page.locator(".transcript-turn mark").first()).toBeVisible();
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
    .fill("This needs a follow-up review.");
  await dialog
    .getByRole("button", { name: "Add comment", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await page.reload();
  await page.getByRole("button", { name: "Comments", exact: true }).click();
  dialog = page.getByRole("dialog");
  await expect(
    dialog.getByText("This needs a follow-up review.", { exact: true }),
  ).toBeVisible();
  await dialog.getByRole("button", { name: "Edit", exact: true }).click();
  const editor = page.getByRole("dialog", {
    name: "Edit comment",
    exact: true,
  });
  await editor
    .getByRole("textbox", { name: "Comment", exact: true })
    .fill("Review confirmed.");
  await editor
    .getByRole("button", { name: "Save annotation", exact: true })
    .click();
  await expect(editor).toHaveCount(0);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close dialog" })
    .click();
  await page.getByRole("button", { name: "Soundbites", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Save a soundbite", exact: true })
    .click();
  const clip = page.getByRole("dialog", {
    name: "Save soundbite",
    exact: true,
  });
  await clip
    .getByLabel("Soundbite name", { exact: true })
    .fill("Opening moment");
  await clip.getByLabel("Start seconds", { exact: true }).fill("0");
  await clip.getByLabel("End seconds", { exact: true }).fill("1");
  await clip
    .getByRole("button", { name: "Save soundbite", exact: true })
    .click();
  await expect(clip).toHaveCount(0);
  const downloadPromise = page.waitForEvent("download");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Export text", exact: true })
    .click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("soundbite.txt");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Play interval", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".soundbite-state")).toContainText("Complete");
  expect(
    await page.getByRole("slider", { name: "Seek meeting" }).inputValue(),
  ).toBe("1000");
  await expect(
    page.getByRole("button", { name: "Play", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Highlights", exact: true }).click();
  await expect(
    page
      .getByRole("dialog")
      .getByText("Revisit the first phrase", { exact: true }),
  ).toBeVisible();
  const axe = await new AxeBuilder({ page }).analyze();
  expect(
    axe.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    ),
  ).toEqual([]);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Edit", exact: true })
    .click();
  const highlight = page.getByRole("dialog", {
    name: "Edit highlight",
    exact: true,
  });
  await highlight
    .getByRole("button", { name: "Delete annotation…", exact: true })
    .click();
  await page
    .getByRole("dialog", { name: "Delete annotation?", exact: true })
    .getByRole("button", { name: "Delete annotation", exact: true })
    .click();
  await expect(
    page
      .getByRole("dialog")
      .getByText("Revisit the first phrase", { exact: true }),
  ).toHaveCount(0);
});
