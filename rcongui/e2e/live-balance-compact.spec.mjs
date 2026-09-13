import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

const card = (page) =>
  page.getByRole("region", { name: "Live-Balance-Assistent" });
const toggle = (page) =>
  card(page).getByRole("switch", { name: "Live-Balance-Details anzeigen" });
async function compact(page) {
  await expect(toggle(page)).toBeEnabled();
  await expect(toggle(page)).toBeChecked();
  await toggle(page).click();
  await expect(toggle(page)).not.toBeChecked();
  await expect(
    card(page).getByText("Geschätzte Teamstärke", { exact: true })
  ).toHaveCount(0);
}
async function expectSummary(page, hasProjection = false) {
  await expect(
    card(page).getByRole("img", { name: /^Stärke-Index Live:/ })
  ).toBeVisible();
  const forecast = card(page).getByRole("img", {
    name: /^Stärke-Index-Prognose:/,
  });
  if (hasProjection) await expect(forecast).toBeVisible();
  else {
    await expect(forecast).toHaveCount(0);
    await expect(
      card(page).getByText("Keine Prognose verfügbar", { exact: true }).first()
    ).toBeVisible();
  }
  await expect(
    card(page).getByRole("button", { name: "Beobachten", exact: true })
  ).toBeVisible();
}

test("compact mode keeps live/projection indices and actions, and survives reload", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live");
  await compact(page);
  await expectSummary(page);
  await expect(
    card(page).getByRole("button", { name: "Kein Eingriff nötig" })
  ).toBeVisible();
  await page.reload();
  await expect(toggle(page)).not.toBeChecked();
  await expectSummary(page);
  await toggle(page).click();
  await expect(toggle(page)).toBeChecked();
  await expect(
    card(page).getByText("Geschätzte Teamstärke", { exact: true })
  ).toBeVisible();
});

test("status-card reset preserves compact mode and another account keeps its own default", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live");
  await compact(page);
  await page
    .getByRole("button", { name: "Live-Ansicht anpassen", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Live-Ansicht anpassen" });
  await dialog
    .getByRole("button", { name: "Standard: nur Spielstand und nächste Karte" })
    .click();
  await dialog.getByRole("button", { name: "Speichern", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(toggle(page)).not.toBeChecked();
  await openDemoPage(page, "/views/live", { query: { demo_role: "viewer" } });
  await expect(toggle(page)).toBeChecked();
  await openDemoPage(page, "/views/live");
  await expect(toggle(page)).not.toBeChecked();
});

test("an imbalance stays compact and an intervention can still be reviewed without execution", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live");
  await compact(page);
  await openDemoPage(page, "/views/live", {
    query: { demo_balance: "unbalanced" },
  });
  await expect(toggle(page)).not.toBeChecked();
  await expect(
    card(page).getByRole("heading", { name: "Spielerzahl unausgeglichen" })
  ).toBeVisible();
  await expectSummary(page, true);
  await card(page)
    .getByRole("button", { name: "Squad-Wechsel prüfen", exact: true })
    .click();
  const review = page.getByRole("dialog", {
    name: "Koordinierten Squad-Wechsel prüfen",
  });
  await expect(review).toBeVisible();
  await review.getByRole("button", { name: "Schließen", exact: true }).click();
  await expect(review).toHaveCount(0);
  await expect(toggle(page)).not.toBeChecked();
});

test("failed saving leaves the prior display unchanged and explains the error", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live", {
    query: { demo_live_view_error: "save" },
  });
  await expect(toggle(page)).toBeEnabled();
  await toggle(page).click();
  await expect(card(page).getByRole("alert")).toContainText(
    "Nicht gespeichert"
  );
  await expect(toggle(page)).toBeChecked();
  await expect(
    card(page).getByText("Geschätzte Teamstärke", { exact: true })
  ).toBeVisible();
});

test("mobile compact mode keeps bars/actions visible and supports keyboard toggling", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/views/live");
  await compact(page);
  await expectSummary(page);
  await expectNoHorizontalPageOverflow(page);
  await toggle(page).press("Space");
  await expect(toggle(page)).toBeChecked();
  await toggle(page).press("Space");
  await expect(toggle(page)).not.toBeChecked();
  await expectSummary(page);
});
