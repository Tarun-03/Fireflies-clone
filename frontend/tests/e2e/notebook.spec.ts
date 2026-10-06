import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("notebook search, seeking, follow, notes, and responsive playback", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.goto("/");
  await page.locator(".meeting-title").first().click();
  await expect(
    page.getByRole("heading", { name: "Transcript", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".transcript-turn")).toHaveCount(40);
  const seeks = page.getByRole("button", { name: /^Seek to/ });
  await seeks.nth(5).click();
  const slider = page.getByRole("slider", { name: "Seek meeting" });
  expect(Number(await slider.inputValue())).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Pause", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await page.getByRole("textbox", { name: "Search transcript" }).fill("review");
  await expect(
    page.locator(".transcript-results .muted").first(),
  ).toContainText("matching turns");
  await expect(page.locator(".search-hit").first()).toBeVisible();
  await page.locator(".search-hit").first().click();
  await page.getByRole("textbox", { name: "Search transcript" }).press("Space");
  await expect(
    page.getByRole("button", { name: "Play", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear", exact: true }).click();
  await page
    .getByRole("region", { name: "Transcript", exact: true })
    .getByRole("button", { name: "Follow on" })
    .click();
  await expect(page.getByRole("button", { name: "Follow off" })).toBeVisible();
  await page
    .getByRole("textbox", { name: "Personal notes" })
    .fill("Browser-verified note: café 😀");
  await page.getByRole("button", { name: "Save notes" }).click();
  await expect(page.locator("[aria-live=polite]")).toContainText("Notes saved");
  await page.reload();
  await expect(
    page.getByRole("textbox", { name: "Personal notes" }),
  ).toHaveValue("Browser-verified note: café 😀");
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    if (width <= 800)
      await page.getByRole("tab", { name: "Transcript", exact: true }).click();
    await expect(
      page.getByRole("slider", { name: "Seek meeting" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    const axe = await new AxeBuilder({ page }).analyze();
    expect(
      axe.violations.filter((v) =>
        ["serious", "critical"].includes(v.impact ?? ""),
      ),
    ).toEqual([]);
    await page.screenshot({
      path: `../docs/screenshots/notebook-${width}.png`,
      fullPage: true,
    });
  }
});

test("seeks to unloaded turns without mounting a large transcript", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".meeting-title")).toHaveCount(8);
  const id = await page.evaluate(async () => {
    const token = await (await fetch("/api/session/csrf")).json();
    const response = await fetch("/api/v1/meetings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": token.csrf_token,
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({
        title: "Long synthetic transcript",
        occurred_at: "2026-10-06T00:00:00Z",
        duration_ms: 3000000,
        segments: Array.from({ length: 3000 }, (_, i) => ({
          speaker: "Test speaker",
          start_ms: i * 1000,
          end_ms: i * 1000 + 900,
          text: `Distinct turn ${i}: synthetic browser timing verification.`,
        })),
      }),
    });
    if (!response.ok) throw new Error(await response.text());
    return (await response.json()).id as string;
  });
  await page.goto(`/meetings/${id}`);
  const slider = page.getByRole("slider", { name: "Seek meeting" });
  await expect(slider).toBeVisible();
  await slider.fill("2980500");
  await expect(page.locator(".transcript-turn.current")).toContainText(
    "Distinct turn 2980",
  );
  expect(await page.locator(".transcript-turn").count()).toBeLessThanOrEqual(
    60,
  );
  await page.locator(".transcript-scroll").hover();
  await page.mouse.wheel(0, 200);
  await expect(page.getByRole("button", { name: "Follow off" })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 900 });
  await page.getByRole("tab", { name: "Transcript", exact: true }).click();
  expect(await slider.inputValue()).toBe("2980500");
  await page.getByRole("tab", { name: "Summary", exact: true }).click();
  await page.getByRole("tab", { name: "Transcript", exact: true }).click();
  expect(await slider.inputValue()).toBe("2980500");
});
