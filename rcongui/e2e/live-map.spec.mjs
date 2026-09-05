import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

test.use({ viewport: VIEWPORTS.desktop });

test("100 synthetic players, search, replay and protected evidence", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await openDemoPage(page, "/views/live-map");
  const view = page.getByTestId("live-map-page");
  await expect(view.locator('svg g[role="button"]')).toHaveCount(100);
  await expect(view.getByText("DEMO · Synthetische Testdaten")).toBeVisible();
  await view
    .getByLabel("Spieler suchen", { exact: true })
    .fill("Demo Spieler 01");
  await expect(view.locator('svg g[role="button"]')).toHaveCount(1);
  await view.locator('svg g[role="button"]').click();
  await expect(
    view.getByRole("button", { name: "Verfolgen", exact: true })
  ).toBeEnabled();
  await view.getByRole("button", { name: "Vergrößern", exact: true }).click();
  await expect(view.getByText("150 %")).toBeVisible();
  await view.locator("summary").filter({ hasText: "Begegnungen" }).click();
  await view
    .getByRole("button", { name: "Ort im Rückblick ansehen" })
    .first()
    .click();
  await expect(view.getByTestId("encounter-marker")).toBeVisible();
  await view.getByRole("button", { name: "Zurück zu Live" }).click();
  await view
    .getByRole("button", { name: "Als Fall sichern", exact: true })
    .click();
  await expect(
    view.getByRole("button", { name: "Ausschnitt ansehen" })
  ).toBeVisible();
  await view.getByRole("button", { name: "Ausschnitt ansehen" }).click();
  await expect(
    view.getByRole("button", { name: "Zurück zu Live" })
  ).toBeVisible();
  await expect(
    view.getByRole("button", { name: "Übernehmen", exact: true })
  ).toHaveCount(0);
  await view.getByRole("button", { name: "Zurück zu Live" }).click();
  await view.getByRole("button", { name: "Verlauf laden" }).click();
  await expect(
    view.getByText(/Im Rückblick werden keine aktuellen Live-Hinweise/)
  ).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
  await page.screenshot({
    path: "test-results/live-map-desktop.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("unverified maps never display precise markers", async ({ page }) => {
  await openDemoPage(page, "/views/live-map", {
    query: { tacticalScenario: "uncalibrated" },
  });
  await expect(
    page.getByText("Kartenabbildung noch nicht geprüft")
  ).toBeVisible();
  await expect(page.locator('svg g[role="button"]')).toHaveCount(0);
});

test("ordinary viewer gets no tactical page", async ({ page }) => {
  await openDemoPage(page, "/views/live-map", {
    query: { demo_role: "viewer" },
  });
  await expect(
    page.getByText(/ausdrückliche Freigabe für taktische Daten/)
  ).toBeVisible();
  await expect(page.locator('svg g[role="button"]')).toHaveCount(0);
});

test("mobile switches between map and inspector without overflow", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/views/live-map");
  await page.getByRole("tab", { name: "Details & Monitor" }).click();
  await expect(
    page.getByText("Ausgewählter Spieler", { exact: true })
  ).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
  await page.screenshot({
    path: "test-results/live-map-mobile.png",
    fullPage: true,
  });
});
