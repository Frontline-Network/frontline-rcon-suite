import { expect, test } from "@playwright/test";
import { collectRuntimeErrors, openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.use({ viewport: VIEWPORTS.desktop });

test("compact records preserve cross-page action recipients and load history only on demand", async ({ page }) => {
  const errors = collectRuntimeErrors(page);
  await openDemoPage(page, "/records/players", {
    query: { page_size: 2, demo_records_projection: 1 },
  });
  await page.getByRole("button", { name: "Kartenansicht", exact: true }).click();
  const chooseRaven = page.getByRole("checkbox", { name: "FLN_Raven auswählen", exact: true });
  await expect(chooseRaven).toBeVisible();
  await chooseRaven.check();
  expect(await page.evaluate(() => window.__CRCON_DEMO_PROTECTED_REQUESTS__.includes("/api/get_player_profile"))).toBe(false);

  await page.getByRole("link", { name: "Nächste Seite", exact: true }).first().click();
  const chooseValkyrie = page.getByRole("checkbox", { name: "FLN_Valkyrie auswählen", exact: true });
  await expect(chooseValkyrie).toBeVisible();
  await chooseValkyrie.check();
  const actions = page.getByRole("region", { name: "Aktionen für ausgewählte Spieler", exact: true });
  await expect(actions.getByText("Ausgewählt: 2", { exact: true })).toBeVisible();
  await actions.getByRole("button", { name: "VIP hinzufügen", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("FLN_Raven", { exact: true })).toBeVisible();
  await expect(dialog.getByText("FLN_Valkyrie", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "Abbrechen", exact: true }).click();

  await page.getByRole("link", { name: "Vorherige Seite", exact: true }).first().click();
  await expect(chooseRaven).toBeChecked();
  await chooseRaven.uncheck();
  await expect(actions.getByText("Ausgewählt: 1", { exact: true })).toBeVisible();
  await actions.getByRole("button", { name: "Auswahl aufheben", exact: true }).click();
  await expect(actions).toHaveCount(0);
  await expect(chooseRaven).not.toBeChecked();

  const requests = await page.evaluate(() => window.__CRCON_DEMO_RECORD_REQUESTS__);
  expect(requests.map(({ page: requestedPage }) => requestedPage)).toEqual([1, 2, 1]);
  expect(requests.every(({ compact, page_size }) => compact === true && page_size === 2)).toBe(true);
  expect(await page.evaluate(() => window.__CRCON_DEMO_PROTECTED_REQUESTS__.includes("/api/get_player_profile"))).toBe(false);

  const ravenCard = page.locator(".MuiCard-root").filter({ has: page.getByRole("checkbox", { name: "FLN_Raven auswählen", exact: true }) });
  await ravenCard.getByRole("button", { name: "Spieleraktionen", exact: true }).click();
  await page.getByRole("menuitem", { name: "Profil ansehen", exact: true }).click();
  await expect(page.getByRole("tab", { name: "Administration", exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.__CRCON_DEMO_PROTECTED_REQUESTS__.includes("/api/get_player_profile"))).toBe(true);
  await page.getByRole("tab", { name: "Administration", exact: true }).click();
  await page.getByRole("tabpanel").getByRole("button", { name: /^PUNISH Leitstelle/ }).click();
  await expect(page.getByText("Teamkill", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
