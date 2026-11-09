import { expect, test } from "@playwright/test";
import { openDemoPage } from "./helpers.mjs";

test.use({ viewport: { width: 1920, height: 1000 } });
const requests = (page) =>
  page.evaluate(() => window.__CRCON_DEMO_LOG_REQUESTS__ ?? []);

test("polling uses an event cursor; scrolling pauses without moving the view", async ({
  page,
}) => {
  await page.clock.install();
  await openDemoPage(page, "/views/live");
  await expect
    .poll(async () => (await requests(page)).length)
    .toBeGreaterThan(0);
  expect((await requests(page))[0].cursor_mode).toBe(true);
  // Use real time for the first interval: fake API response timers must finish
  // before React Query schedules its next poll.
  await expect
    .poll(async () => (await requests(page)).some((r) => Boolean(r.after)), {
      timeout: 30_000,
    })
    .toBe(true);
  const stream = page.getByTestId("live-event-stream");
  await stream.evaluate((el) => {
    el.scrollTop = 120;
  });
  await expect(page.getByText("Pausiert", { exact: true })).toBeVisible();
  const before = (await requests(page)).length;
  await page.clock.fastForward(31_000);
  expect((await requests(page)).length).toBe(before);
  expect(await stream.evaluate((el) => el.scrollTop)).toBeGreaterThan(48);
  await page
    .getByRole("button", { name: "Live fortsetzen", exact: true })
    .click();
  await expect.poll(() => stream.evaluate((el) => el.scrollTop)).toBe(0);
  await expect
    .poll(async () => (await requests(page)).length)
    .toBeGreaterThan(before);
});

test("older logs use a separate cursor and filter changes start a new window", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live");
  await page
    .getByRole("button", { name: "Erweiterte Filter", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Erweiterte Filter" });
  await dialog.getByRole("tab", { name: "Datenabruf", exact: true }).click();
  await dialog
    .getByRole("spinbutton", { name: "Abruflimit für Protokolle" })
    .fill("1000");
  await dialog.getByRole("button", { name: "Übernehmen", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Ältere Meldungen laden", exact: true })
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Ältere Meldungen laden", exact: true })
    .click();
  await expect
    .poll(async () => (await requests(page)).some((r) => Boolean(r.before)))
    .toBe(true);
  await expect(page.getByText("Pausiert", { exact: true })).toBeVisible();
  expect((await requests(page)).every((r) => r.end <= 500)).toBe(true);
  const before = (await requests(page)).length;
  await page
    .getByRole("button", { name: "Erweiterte Filter", exact: true })
    .click();
  await dialog.getByRole("tab", { name: "Datenabruf", exact: true }).click();
  await dialog
    .getByRole("spinbutton", { name: "Abruflimit für Protokolle" })
    .fill("750");
  await dialog.getByRole("button", { name: "Übernehmen", exact: true }).click();
  await expect
    .poll(async () => (await requests(page)).length)
    .toBeGreaterThan(before);
  const latest = (await requests(page)).at(-1);
  expect(latest.after).toBeUndefined();
  expect(latest.before).toBeUndefined();
  await expect(page.getByText("Pausiert", { exact: true })).toHaveCount(0);
});

test("theme chunk failure shows a recoverable English error instead of a blank page", async ({
  page,
}) => {
  await page.addInitScript(() => localStorage.setItem("crcon.language", "en"));
  await page.route(
    /\/themes\/(default\/getDefaultTheme|wardogs\/getWardogsTheme)/,
    (route) => route.abort()
  );
  await page.goto("/views/live");
  await expect(
    page.getByRole("heading", { name: "Appearance could not be loaded" })
  ).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(
    "Your saved settings will be kept"
  );
  await page.unrouteAll();
  await page.getByRole("button", { name: "Reload page", exact: true }).click();
  await expect(page.locator("#main-content")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Appearance could not be loaded" })
  ).toHaveCount(0);
});
