import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFile } from "node:fs/promises";

test("global evidence search, persistent grounded chat, and real exports", async ({
  page,
}) => {
  await page.goto("/");
  await page.keyboard.press("ControlOrMeta+k");
  let dialog = page.getByRole("dialog");
  await dialog
    .getByRole("textbox", { name: "Search all meetings" })
    .fill("budget");
  await dialog
    .getByRole("combobox", { name: "Search in", exact: true })
    .selectOption("transcript");
  await expect(dialog.locator(".global-search-hit").first()).toBeVisible();
  await dialog.locator(".global-search-hit").first().click();
  await expect(page).toHaveURL(/segment=/);
  await expect(page.locator(".transcript-turn.current")).toBeVisible();
  await page
    .getByRole("button", { name: "Meeting assistant", exact: true })
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("textbox", { name: "Ask a question" })
    .fill("What about the budget?");
  await dialog
    .getByRole("button", { name: "Ask meeting", exact: true })
    .click();
  await expect(dialog.locator(".chat-message.assistant")).toContainText(
    "Relevant transcript excerpts",
  );
  expect(
    (await new AxeBuilder({ page }).analyze()).violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    ),
  ).toEqual([]);
  await page.reload();
  await page
    .getByRole("button", { name: "Meeting assistant", exact: true })
    .click();
  dialog = page.getByRole("dialog");
  await expect(dialog.locator(".chat-message.user")).toContainText(
    "What about the budget?",
  );
  await dialog.locator(".chat-citations button").first().click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Export", exact: true }).click();
  dialog = page.getByRole("dialog");
  for (const format of ["txt", "md", "pdf"]) {
    await dialog
      .getByRole("combobox", { name: "Format", exact: true })
      .selectOption(format);
    const pending = page.waitForEvent("download");
    await dialog.getByRole("button", { name: "Download", exact: true }).click();
    const download = await pending;
    expect(download.suggestedFilename()).toBe(`meeting-part-1-of-1.${format}`);
    const content = await readFile((await download.path())!);
    expect(content.length).toBeLessThan(4 * 1024 * 1024);
    expect(content.toString()).toContain(
      format === "pdf" ? "%PDF-" : "Transcript",
    );
  }
  await dialog.getByRole("button", { name: "Close dialog" }).click();
  await page
    .getByRole("button", { name: "Meeting assistant", exact: true })
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("button", { name: "Clear history…", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Confirm clear history", exact: true })
    .click();
  await expect(dialog.locator(".chat-message")).toHaveCount(0);
});
