import { expect, test } from "@playwright/test";

test("isolated browser sessions, BFF protections, and failed mutation recovery", async ({
  page,
  browser,
}) => {
  await page.goto("/");
  await expect(page.locator(".meeting-title")).toHaveCount(8);
  const meeting = await page.evaluate(
    async () => (await (await fetch("/api/v1/meetings")).json()).items[0],
  );
  const second = await browser.newContext();
  const foreign = await second.newPage();
  await foreign.goto("/");
  await expect(foreign.locator(".meeting-title")).toHaveCount(8);
  const status = await foreign.evaluate(async (id) => {
    const token = (await (await fetch("/api/session/csrf")).json()).csrf_token;
    return await Promise.all(
      ["", "/transcript", "/chat", "/export?format=pdf"].map(
        async (path) => (await fetch(`/api/v1/meetings/${id}${path}`)).status,
      ),
    ).then(async (statuses) => [
      ...statuses,
      (
        await fetch(`/api/v1/meetings/${id}`, {
          method: "DELETE",
          headers: { "X-CSRF-Token": token, "If-Match": "1" },
        })
      ).status,
    ]);
  }, meeting.id);
  expect(status).toEqual([404, 404, 404, 404, 404]);
  await second.close();
  const rejected = await page.evaluate(
    async (id) => [
      (
        await fetch(`/api/v1/meetings/${id}`, {
          method: "DELETE",
          headers: { "If-Match": "1" },
        })
      ).status,
      (await fetch("/api/v1/demo/session")).status,
      (
        await fetch("/api/v1/meetings", {
          headers: {
            Authorization: "Bearer forged",
            "X-Demo-Session": crypto.randomUUID(),
          },
        })
      ).status,
    ],
    meeting.id,
  );
  expect(rejected).toEqual([403, 404, 200]);
  const response = await page.request.get("/", {
    headers: { Origin: "https://evil.invalid" },
  });
  expect(response.headers()["content-security-policy"]).toContain(
    "script-src 'self' 'nonce-",
  );
  expect(response.headers()["content-security-policy"]).not.toContain(
    "unsafe-eval",
  );
  expect(response.headers()["x-frame-options"]).toBe("DENY");
  expect(
    (
      await page.request.delete(`/api/v1/meetings/${meeting.id}`, {
        headers: { Origin: "https://evil.invalid", "If-Match": "1" },
      })
    ).status(),
  ).toBe(403);
  await page.goto(`/meetings/${meeting.id}`);
  await page
    .getByRole("textbox", { name: "Personal notes", exact: true })
    .fill("Draft survives the outage");
  await page.route(
    `**/api/v1/meetings/${meeting.id}/summary`,
    async (route) => {
      if (route.request().method() === "PATCH")
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            error: { code: "unavailable", message: "Temporary test outage" },
          }),
        });
      else await route.continue();
    },
  );
  await page.getByRole("button", { name: "Save notes", exact: true }).click();
  await expect(page.locator(".error-notice")).toContainText(
    "Temporary test outage",
  );
  await expect(
    page.getByRole("textbox", { name: "Personal notes", exact: true }),
  ).toHaveValue("Draft survives the outage");
  await page.unroute(`**/api/v1/meetings/${meeting.id}/summary`);
  await page.getByRole("button", { name: "Save notes", exact: true }).click();
  await expect(page.locator("[aria-live=polite]")).toContainText("Notes saved");
  await page.goto("/meetings/00000000-0000-0000-0000-000000000000");
  await expect(page.locator(".error-notice")).toContainText(
    /not|available|found/i,
  );
});
