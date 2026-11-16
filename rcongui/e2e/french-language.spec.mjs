import { expect, test } from "@playwright/test";
import { VIEWPORTS, expectNoHorizontalPageOverflow } from "./helpers.mjs";

const frenchAsset = /\/(?:src\/i18n\/locales\/fr\.js|assets\/fr-[\w-]+\.js)(?:\?.*)?$/;

test("failed language download keeps the current language and allows retry", async ({ page }) => {
  let failures = 0;
  await page.route(frenchAsset, async (route) => {
    if (failures++ < 2) await route.abort();
    else await route.continue();
  });
  await page.addInitScript(() => localStorage.setItem("crcon.language", "de"));
  await page.goto("/records/game-logs", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Sprache", exact: true }).click();
  await page.getByRole("menuitem", { name: "Français", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Die Sprache konnte nicht geladen werden" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
  expect(await page.evaluate(() => localStorage.getItem("crcon.language"))).toBe("de");
  await page.getByRole("menuitem", { name: "Français", exact: true }).click();
  await expect.poll(() => failures).toBeGreaterThanOrEqual(2);
  await expect(page.getByRole("alert").filter({ hasText: "Die Sprache konnte nicht geladen werden" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
  await page.getByRole("menuitem", { name: "Français", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  expect(await page.evaluate(() => localStorage.getItem("crcon.language"))).toBe("fr");
});

test("failed saved French catalog preserves preference and shows a startup error", async ({ page }) => {
  await page.route(frenchAsset, (route) => route.abort());
  await page.addInitScript(() => localStorage.setItem("crcon.language", "fr"));
  await page.goto("/records/game-logs", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("alert").filter({ hasText: "The language could not be loaded" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  expect(await page.evaluate(() => localStorage.getItem("crcon.language"))).toBe("fr");
  await page.unroute(frenchAsset);
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
});

test("release dialog reports a failed language download and supports retry", async ({ page }) => {
  let failures = 0;
  await page.route(frenchAsset, async (route) => {
    if (failures++ === 0) await route.abort();
    else await route.continue();
  });
  await page.addInitScript(() => {
    localStorage.setItem("crcon.language", "de");
    localStorage.removeItem("crcon.preview.highlights:v0.8.8:preview-user");
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible({ timeout: 20000 });
  await dialog.getByRole("button", { name: "Français", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("Die Sprache konnte nicht geladen werden");
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
  await dialog.getByRole("button", { name: "Français", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  await expect(dialog.getByRole("alert")).toHaveCount(0);
});

test("the last language selection wins when French loads slowly", async ({ page }) => {
  let releaseFrench;
  const frenchBlocked = new Promise((resolve) => { releaseFrench = resolve; });
  let frenchRequested;
  const requestStarted = new Promise((resolve) => { frenchRequested = resolve; });
  // Vite serves the source module in development and a hashed asset in builds.
  await page.route(/\/(?:src\/i18n\/locales\/fr\.js|assets\/fr-[\w-]+\.js)(?:\?.*)?$/, async (route) => {
    frenchRequested(route.request().url());
    await frenchBlocked;
    await route.continue();
  });
  await page.addInitScript(() => window.localStorage.setItem("crcon.language", "de"));
  await page.goto("/records/game-logs", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Sprache", exact: true }).click();
  await page.getByRole("menuitem", { name: "Français", exact: true }).click();
  const frenchUrl = await requestStarted;
  await page.getByRole("menuitem", { name: "English", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  releaseFrench();
  await page.evaluate(async (url) => { await import(/* @vite-ignore */ url); }, frenchUrl);
  await expect(page.getByRole("heading", { name: "Game logs", exact: true })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect.poll(() => page.evaluate(() => localStorage.getItem("crcon.language"))).toBe("en");
});

test("French can be selected, persists across reload, and switches back to German and English", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.desktop);
  await page.goto("/records/game-logs", { waitUntil: "domcontentloaded" });
  const main = page.locator("#main-content");
  await expect(main).toBeVisible();
  await expect(main.getByRole("heading", { name: "Spielprotokolle", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sprache", exact: true }).click();
  await page.getByRole("menuitem", { name: "Français", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("crcon.language"))).toBe("fr");
  await expect(main.getByRole("heading", { name: "Journaux de jeu", exact: true })).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  await expect(main.getByRole("heading", { name: "Journaux de jeu", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Langue", exact: true }).click();
  await page.getByRole("menuitem", { name: "English", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(main.getByRole("heading", { name: "Game logs", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Language", exact: true }).click();
  await page.getByRole("menuitem", { name: "Deutsch", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
  await expect(main.getByRole("heading", { name: "Spielprotokolle", exact: true })).toBeVisible();
});

test("French loads after a settings page has already registered its lazy panels", async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem("crcon.language", "de"));
  await page.goto("/settings/others/autobalancer", { waitUntil: "domcontentloaded" });
  await page.locator("#autobalancer-settings").click();
  await expect(page.getByRole("heading", { name: "Autobalancer", exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Sprache", exact: true }).click();
  await page.getByRole("menuitem", { name: "Français", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  await expect(page.getByRole("heading", { name: "Équilibrage automatique", exact: true })).toBeVisible();
  await expect(page.getByText("Informer les joueurs", { exact: true })).toBeVisible();
});
