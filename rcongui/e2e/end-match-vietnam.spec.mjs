import { test, expect } from "@playwright/test";
import { openDemoPage } from "./helpers.mjs";

const api = process.env.REACT_APP_API_URL;
const base = api && api !== "undefined" ? api.replace(/\/+$/, "") : "";

for (const [language, mortar, helicopter, save, saved] of [
  ["de", "Mörser", "Hubschrauber", "Speichern", "Einstellungen gespeichert."],
  ["en", "Mortar", "Helicopter", "Save", "Settings saved."],
  ["fr", "Mortier", "Hélicoptère", "Enregistrer", "Paramètres enregistrés."],
]) {
  test(`Vietnam squad types can be saved in ${language}`, async ({ page }) => {
    await openDemoPage(page, "/settings/others/end-match-stats", { language });
    await page.getByLabel(mortar, { exact: true }).check();
    await page.getByLabel(helicopter, { exact: true }).check();
    await page.getByRole("button", { name: save, exact: true }).click();
    await expect(page.getByRole("status").filter({ hasText: saved })).toBeVisible();
    await expect(page.getByLabel(mortar, { exact: true })).toBeChecked();
    await expect(page.getByLabel(helicopter, { exact: true })).toBeChecked();
    const values = await page.evaluate(async (endpoint) =>
      (await (await fetch(endpoint)).json()).result.unit_types,
      `${base}/get_end_match_stats_config`);
    expect(values).toEqual(expect.arrayContaining(["mortar", "helicopter"]));
  });
}
