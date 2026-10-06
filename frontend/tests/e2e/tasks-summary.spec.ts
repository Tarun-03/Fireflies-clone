import { expect, test } from "@playwright/test";
test("manual tasks, notes, and regeneration preserve personal work", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator(".meeting-title").first().click();
  await page
    .getByRole("button", { name: "Add action item", exact: true })
    .click();
  let dialog = page.getByRole("dialog");
  await dialog
    .getByRole("textbox", { name: "Action item", exact: true })
    .fill("Verify the synthetic pilot checklist");
  await dialog
    .getByRole("combobox", { name: "Owner", exact: true })
    .selectOption({ index: 1 });
  await dialog.getByLabel("Due date", { exact: true }).fill("2026-10-20");
  await dialog.getByRole("button", { name: "Save task", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  const complete = page.getByRole("checkbox", {
    name: "Complete Verify the synthetic pilot checklist",
    exact: true,
  });
  await complete.click();
  await expect(
    page.getByRole("checkbox", {
      name: "Reopen Verify the synthetic pilot checklist",
      exact: true,
    }),
  ).toBeChecked();
  await page
    .getByRole("textbox", { name: "Personal notes", exact: true })
    .fill("Keep this personal note after regeneration.");
  await page.getByRole("button", { name: "Save notes", exact: true }).click();
  await expect(page.locator("[aria-live=polite]")).toContainText("Notes saved");
  await page
    .getByRole("textbox", { name: "Personal notes", exact: true })
    .fill("Unsaved notes draft stays here.");
  await page
    .getByRole("button", { name: "Regenerate notes", exact: true })
    .click();
  dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "Regenerate", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByRole("textbox", { name: "Personal notes", exact: true }),
  ).toHaveValue("Unsaved notes draft stays here.");
  await page.reload();
  await expect(
    page.getByRole("textbox", { name: "Personal notes", exact: true }),
  ).toHaveValue("Keep this personal note after regeneration.");
  await expect(
    page.getByRole("checkbox", {
      name: "Reopen Verify the synthetic pilot checklist",
      exact: true,
    }),
  ).toBeChecked();
  await page
    .getByRole("button", {
      name: "Edit task: Verify the synthetic pilot checklist",
      exact: true,
    })
    .click();
  dialog = page.getByRole("dialog");
  await expect(dialog.getByLabel("Due date", { exact: true })).toHaveValue(
    "2026-10-20",
  );
  await dialog
    .getByRole("textbox", { name: "Action item", exact: true })
    .fill("Verify the revised pilot checklist");
  await dialog.getByRole("button", { name: "Save task", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page.getByRole("link", { name: "Action items", exact: true }).click();
  await expect(
    page.getByRole("checkbox", {
      name: "Reopen Verify the revised pilot checklist",
      exact: true,
    }),
  ).toBeChecked();
  await page
    .getByRole("checkbox", {
      name: "Reopen Verify the revised pilot checklist",
      exact: true,
    })
    .click();
  await page
    .getByRole("button", {
      name: "Edit task: Verify the revised pilot checklist",
      exact: true,
    })
    .click();
  dialog = page.getByRole("dialog");
  await dialog
    .getByRole("button", { name: "Delete task…", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Delete task", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByText("Verify the revised pilot checklist", { exact: true }),
  ).toHaveCount(0);
});
