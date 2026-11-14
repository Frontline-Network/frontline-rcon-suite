import { expect, test } from "@playwright/test";
import { VIEWPORTS, expectNoHorizontalPageOverflow } from "./helpers.mjs";

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
