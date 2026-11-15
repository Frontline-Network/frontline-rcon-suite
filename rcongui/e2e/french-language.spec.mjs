import { expect, test } from "@playwright/test";
import { VIEWPORTS, expectNoHorizontalPageOverflow } from "./helpers.mjs";

test("the last language selection wins when French loads slowly", async ({ page }) => {
  let releaseFrench;
  const frenchBlocked = new Promise((resolve) => { releaseFrench = resolve; });
  let frenchRequested;
  const requestStarted = new Promise((resolve) => { frenchRequested = resolve; });
  await page.route("**/src/i18n/locales/fr.js*", async (route) => {
    frenchRequested();
    await frenchBlocked;
    await route.continue();
  });
  await page.addInitScript(() => window.localStorage.setItem("crcon.language", "de"));
  await page.goto("/records/game-logs", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Sprache", exact: true }).click();
  await page.getByRole("menuitem", { name: "Français", exact: true }).click();
  await requestStarted;
  await page.getByRole("menuitem", { name: "English", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  releaseFrench();
  await page.evaluate(async () => {
    const module = await import("/src/i18n/index.js");
    await module.ensureLanguageLoaded("fr");
  });
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
