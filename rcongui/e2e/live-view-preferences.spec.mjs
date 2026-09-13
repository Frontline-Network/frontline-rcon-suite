import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

const statusCards = (page) =>
  page.getByRole("region", { name: "Handlungsbedarf und Gefechtsstatus" });
// Both responsive label variants are mounted; only one is displayed at a time.
// Keep strict matching so two visible copies would still fail the assertion.
const visibleStatusLabel = (page, text) =>
  statusCards(page).getByText(text, { exact: true }).filter({ visible: true });
async function openSettings(page) {
  await page
    .getByRole("button", { name: "Live-Ansicht anpassen", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Live-Ansicht anpassen" });
  await expect(
    dialog.getByRole("button", { name: "Speichern", exact: true })
  ).toBeEnabled();
  return dialog;
}
async function save(dialog) {
  await dialog.getByRole("button", { name: "Speichern", exact: true }).click();
  await expect(dialog).toHaveCount(0);
}

test("defaults to score and next map, saves immediately and survives reload", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live");
  const dialog = await openSettings(page);
  for (const name of [
    "Commander-Hinweise (beide Teams)",
    "Truppführer-Hinweise (beide Teams)",
    "VIPs",
    "Beobachtet",
  ]) {
    await expect(
      dialog.getByRole("checkbox", { name, exact: true })
    ).not.toBeChecked();
  }
  for (const name of ["Spielstand", "Nächste Karte"]) {
    await expect(
      dialog.getByRole("checkbox", { name, exact: true })
    ).toBeChecked();
  }
  await dialog.getByRole("checkbox", { name: "VIPs", exact: true }).check();
  await save(dialog);
  await expect(visibleStatusLabel(page, "VIPs")).toBeVisible();
  await page.reload();
  await expect(visibleStatusLabel(page, "VIPs")).toBeVisible();
});

test("cancels unsaved changes and can hide all cards or restore defaults", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live");
  let dialog = await openSettings(page);
  await dialog.getByRole("checkbox", { name: "VIPs", exact: true }).check();
  await dialog.getByRole("button", { name: "Abbrechen", exact: true }).click();
  await expect(
    statusCards(page).getByText("VIPs", { exact: true })
  ).toHaveCount(0);
  dialog = await openSettings(page);
  await expect(
    dialog.getByRole("checkbox", { name: "VIPs", exact: true })
  ).not.toBeChecked();
  await dialog
    .getByRole("checkbox", { name: "Spielstand", exact: true })
    .uncheck();
  await dialog
    .getByRole("checkbox", { name: "Nächste Karte", exact: true })
    .uncheck();
  await save(dialog);
  await expect(statusCards(page)).toHaveCount(0);
  await page.reload();
  dialog = await openSettings(page);
  await expect(
    dialog.getByRole("checkbox", { name: "Spielstand", exact: true })
  ).not.toBeChecked();
  await expect(
    dialog.getByRole("checkbox", { name: "Nächste Karte", exact: true })
  ).not.toBeChecked();
  await dialog
    .getByRole("button", { name: "Standard: nur Spielstand und nächste Karte" })
    .click();
  await save(dialog);
  await expect(visibleStatusLabel(page, "Nächste Karte")).toBeVisible();
});

test("keeps account selections separate, including a viewer account", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live");
  let dialog = await openSettings(page);
  await dialog.getByRole("checkbox", { name: "VIPs", exact: true }).check();
  await save(dialog);
  await openDemoPage(page, "/views/live", { query: { demo_role: "viewer" } });
  dialog = await openSettings(page);
  await expect(
    dialog.getByRole("checkbox", { name: "VIPs", exact: true })
  ).not.toBeChecked();
  await dialog
    .getByRole("checkbox", { name: "Beobachtet", exact: true })
    .check();
  await save(dialog);
  await expect(visibleStatusLabel(page, "Beobachtet")).toBeVisible();
  await openDemoPage(page, "/views/live");
  dialog = await openSettings(page);
  await expect(
    dialog.getByRole("checkbox", { name: "VIPs", exact: true })
  ).toBeChecked();
  await expect(
    dialog.getByRole("checkbox", { name: "Beobachtet", exact: true })
  ).not.toBeChecked();
});

test("keeps saved visibility when saving fails", async ({ page }) => {
  await openDemoPage(page, "/views/live", {
    query: { demo_live_view_error: "save" },
  });
  const dialog = await openSettings(page);
  await dialog.getByRole("checkbox", { name: "VIPs", exact: true }).check();
  await dialog.getByRole("button", { name: "Speichern", exact: true }).click();
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Abbrechen", exact: true }).click();
  await expect(
    statusCards(page).getByText("VIPs", { exact: true })
  ).toHaveCount(0);
});

test("does not overwrite saved preferences when loading fails", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live", {
    query: { demo_live_view_error: "load" },
  });
  await page
    .getByRole("button", { name: "Live-Ansicht anpassen", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("alert")).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Speichern", exact: true })
  ).toBeDisabled();
  await expect(
    dialog.getByRole("button", { name: "Erneut laden", exact: true })
  ).toBeVisible();
});

test("mobile settings stay within the screen and remain usable", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/views/live");
  const dialog = await openSettings(page);
  await expectNoHorizontalPageOverflow(page);
  const bounds = await dialog.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(VIEWPORTS.mobile.width);
  await dialog.getByRole("checkbox", { name: "VIPs", exact: true }).check();
  await save(dialog);
  await expect(visibleStatusLabel(page, "VIPs")).toBeVisible();
});
