import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("library filters, preferences, notifications and responsive layouts", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.goto("/");
  await expect(
    page.getByRole("link", {
      name: "Engineering standup · Search reliability",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Search meeting titles" })
    .fill("standup");
  await expect(page.locator(".meeting-row")).toHaveCount(1);
  await page.reload();
  await expect(page.locator(".meeting-row")).toHaveCount(1);
  await page.getByRole("button", { name: "Clear all", exact: true }).click();
  await expect(page.locator(".meeting-row")).toHaveCount(8);
  await page
    .getByRole("button", { name: "Notifications", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Your private demo workspace is ready",
  );
  await page.getByRole("button", { name: "Mark read" }).click();
  await expect(page.getByRole("button", { name: "Mark read" })).toHaveCount(0);
  await page.keyboard.press("Escape");
  for (const theme of ["light", "dark"] as const) {
    await page.goto("/settings");
    await page
      .getByRole("combobox", { name: "Theme", exact: true })
      .selectOption(theme);
    await page.getByRole("button", { name: "Save preferences" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
    await page.goto("/");
    await expect(page.locator(".meeting-row")).toHaveCount(8);
    for (const width of [390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 960 });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
      const violations = (
        await new AxeBuilder({ page }).analyze()
      ).violations.filter((issue) =>
        ["serious", "critical"].includes(issue.impact ?? ""),
      );
      expect(violations).toEqual([]);
      await page.screenshot({
        path: test.info().outputPath(`library-${theme}-${width}.png`),
        fullPage: true,
      });
    }
  }
});
