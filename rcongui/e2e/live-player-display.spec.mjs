import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

const panel = (page) => page.getByTestId("live-players-panel");
async function openSettings(page) {
  await page
    .getByRole("button", { name: "Tabelle anpassen", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Live-Ansicht anpassen" });
  await expect(
    dialog.getByRole("tab", { name: "Spielertabelle", exact: true })
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    dialog.getByRole("button", { name: "Speichern", exact: true })
  ).toBeEnabled();
  return dialog;
}
async function choose(page, dialog, name, option) {
  await dialog.getByRole("combobox", { name, exact: true }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}
async function save(dialog) {
  await dialog.getByRole("button", { name: "Speichern", exact: true }).click();
  await expect(dialog).toHaveCount(0);
}

test.use({ viewport: VIEWPORTS.desktop });

test("saves custom columns, font and density per account and across reloads", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live");
  let dialog = await openSettings(page);
  await choose(page, dialog, "Schriftgröße", "Groß");
  await choose(page, dialog, "Zeilenabstand", "Großzügig");
  await dialog.getByRole("checkbox", { name: "Rolle", exact: true }).check();
  await dialog.getByRole("checkbox", { name: "Kills", exact: true }).uncheck();
  await expect(
    dialog.getByRole("combobox", { name: "Spaltenprofil" })
  ).toContainText("Eigene Ansicht");
  await save(dialog);
  await expect(
    panel(page).getByRole("columnheader", { name: "Kills", exact: true })
  ).toHaveCount(0);
  const row = panel(page).locator('tr[data-player-row="true"]').first();
  await expect.poll(async () => (await row.boundingBox()).height).toBe(56);
  await expect(row).toHaveCSS("font-size", "18.4px");
  await page.reload();
  await expect(
    panel(page).getByRole("columnheader", { name: "Kills", exact: true })
  ).toHaveCount(0);
  dialog = await openSettings(page);
  await expect(
    dialog.getByRole("checkbox", { name: "Rolle", exact: true })
  ).toBeChecked();
  await expect(
    dialog.getByRole("combobox", { name: "Schriftgröße" })
  ).toContainText("Groß");
  await expect(
    dialog.getByRole("combobox", { name: "Zeilenabstand" })
  ).toContainText("Großzügig");
  await dialog.getByRole("button", { name: "Abbrechen", exact: true }).click();
  await openDemoPage(page, "/views/live", { query: { demo_role: "viewer" } });
  dialog = await openSettings(page);
  await expect(
    dialog.getByRole("combobox", { name: "Spaltenprofil" })
  ).toContainText("Einsatz");
  await expect(
    dialog.getByRole("checkbox", { name: "Kills", exact: true })
  ).toBeChecked();
  await expect(
    dialog.getByRole("combobox", { name: "Schriftgröße" })
  ).toContainText("Klein");
});

test("cancels changes and scopes each reset to its own display section", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live");
  let dialog = await openSettings(page);
  await dialog.getByRole("checkbox", { name: "Kills", exact: true }).uncheck();
  await dialog.getByRole("button", { name: "Abbrechen", exact: true }).click();
  await expect(
    panel(page).getByRole("columnheader", { name: "Kills", exact: true })
  ).toBeVisible();
  dialog = await openSettings(page);
  await dialog.getByRole("checkbox", { name: "Rolle", exact: true }).check();
  await dialog.getByRole("tab", { name: "Statuskarten", exact: true }).click();
  await dialog.getByRole("checkbox", { name: "VIPs", exact: true }).check();
  await dialog
    .getByRole("tab", { name: "Spielertabelle", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Spielertabelle zurücksetzen" })
    .click();
  await dialog.getByRole("tab", { name: "Statuskarten", exact: true }).click();
  await expect(
    dialog.getByRole("checkbox", { name: "VIPs", exact: true })
  ).toBeChecked();
  await dialog
    .getByRole("tab", { name: "Spielertabelle", exact: true })
    .click();
  await dialog.getByRole("checkbox", { name: "Rolle", exact: true }).check();
  await dialog.getByRole("tab", { name: "Statuskarten", exact: true }).click();
  await dialog
    .getByRole("button", { name: "Standard: nur Spielstand und nächste Karte" })
    .click();
  await dialog
    .getByRole("tab", { name: "Spielertabelle", exact: true })
    .click();
  await expect(
    dialog.getByRole("checkbox", { name: "Rolle", exact: true })
  ).toBeChecked();
  await save(dialog);
});

test("a failed save leaves the visible and persisted table unchanged", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live", {
    query: { demo_live_view_error: "save" },
  });
  const dialog = await openSettings(page);
  await dialog.getByRole("checkbox", { name: "Kills", exact: true }).uncheck();
  await dialog.getByRole("button", { name: "Speichern", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("Nicht gespeichert");
  await dialog.getByRole("button", { name: "Abbrechen", exact: true }).click();
  await expect(
    panel(page).getByRole("columnheader", { name: "Kills", exact: true })
  ).toBeVisible();
  await page.reload();
  await expect(
    panel(page).getByRole("columnheader", { name: "Kills", exact: true })
  ).toBeVisible();
});

test("mobile dialog fits, searches columns and keeps save actions reachable", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/views/live");
  const dialog = await openSettings(page);
  await expectNoHorizontalPageOverflow(page);
  const bounds = await dialog.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(VIEWPORTS.mobile.width);
  await dialog
    .getByRole("searchbox", { name: "Spalten suchen" })
    .fill("Fahrzeug");
  await expect(dialog.getByRole("checkbox")).toHaveCount(2);
  await dialog
    .getByRole("checkbox", { name: "Fahrzeug-Kills", exact: true })
    .check();
  await save(dialog);
  const reopened = await openSettings(page);
  await expect(
    reopened.getByRole("checkbox", { name: "Fahrzeug-Kills", exact: true })
  ).toBeChecked();
});
