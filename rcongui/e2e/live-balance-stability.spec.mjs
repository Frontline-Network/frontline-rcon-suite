import { expect, test } from "@playwright/test";
import {
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

test.use({ viewport: VIEWPORTS.desktop });
const card = (page) =>
  page.getByRole("region", { name: "Live-Balance-Assistent" });
const review = (page) =>
  page.getByRole("dialog", { name: "Koordinierten Squad-Wechsel prüfen" });

test("inconsistent server counts block manual switching", async ({ page }) => {
  await openDemoPage(page, "/views/live", { query: { demo_balance: "incomplete" } });
  await expect(card(page).getByText("Live-Daten gerade unvollständig").first()).toBeVisible();
  await card(page).getByRole("button", { name: "Squad-Wechsel prüfen", exact: true }).click();
  await expect(review(page).getByRole("button", {
    name: "Squad(s) informieren und wechseln", exact: true,
  })).toBeDisabled();
});

async function start(page) {
  await openDemoPage(page, "/views/live", {
    query: { demo_balance: "unbalanced" },
  });
  await expect(
    card(page).getByText(/Auswahl bleibt bis zu 60 Sekunden sichtbar/)
  ).toBeVisible();
  await card(page)
    .getByRole("button", { name: "Squad-Wechsel prüfen", exact: true })
    .click();
  await expect(review(page)).toBeVisible();
  await expect(
    review(page).getByRole("button", {
      name: "Squad(s) informieren und wechseln",
      exact: true,
    })
  ).toBeEnabled();
}
async function changeSnapshot(page, value) {
  // Only changes the fake server scenario, without remounting the component.
  await page.evaluate((mode) => {
    const url = new URL(window.location.href);
    url.searchParams.set("demo_balance", mode);
    window.history.replaceState(null, "", url);
  }, value);
}

test("a review holds its exact squad beyond 60 seconds and blocks an invalidated choice", async ({
  page,
}) => {
  await page.clock.install();
  await start(page);
  await expect(
    review(page).getByText("Squad charlie", { exact: true })
  ).toBeVisible();
  await changeSnapshot(page, "changed_squad");
  await page.clock.runFor(11_000);
  await expect(
    review(page).getByText("Vorschlag bitte aktualisieren", { exact: true })
  ).toBeVisible();
  await expect(
    review(page).getByText(/Schließe die Prüfung und wähle „Neu bewerten“/)
  ).toBeVisible();
  await page.clock.fastForward(65_000);
  await expect(
    review(page).getByText("Squad charlie", { exact: true })
  ).toBeVisible();
  await expect(
    review(page).getByRole("button", {
      name: "Squad(s) informieren und wechseln",
      exact: true,
    })
  ).toBeDisabled();
  await expect(
    card(page).getByRole("img", { name: /^Stärke-Index-Prognose:/ })
  ).toHaveCount(0);
  await review(page)
    .getByRole("button", { name: "Schließen", exact: true })
    .click();
  await card(page)
    .getByRole("button", { name: "Squad-Wechsel prüfen", exact: true })
    .click();
  await expect(
    review(page).getByText("Squad delta", { exact: true })
  ).toBeVisible();
});

test("an invalid proposal stays visible until explicitly refreshed; live balance keeps updating", async ({
  page,
}) => {
  await page.clock.install();
  await start(page);
  await review(page)
    .getByRole("button", { name: "Schließen", exact: true })
    .click();
  await changeSnapshot(page, "balanced");
  await page.clock.runFor(11_000);
  await expect(
    card(page).getByRole("heading", { name: "Teams ausgeglichen", exact: true })
  ).toBeVisible();
  await expect(
    card(page)
      .getByRole("status")
      .filter({ hasText: "Aktuell kein Wechsel nötig" })
  ).toBeVisible();
  await expect(
    card(page).getByText(/innerhalb der eingestellten Grenzwerte/)
  ).toBeVisible();
  await expect(
    card(page).getByText(/Kein Eingriff möglich|nicht mehr gültig/)
  ).toHaveCount(0);
  await expect(
    card(page).getByRole("img", { name: /^Stärke-Index Live:/ })
  ).toBeVisible();
  await expect(
    card(page).getByRole("img", { name: /^Stärke-Index-Prognose:/ })
  ).toHaveCount(0);
  await card(page)
    .getByRole("button", { name: "Neu bewerten", exact: true })
    .click();
  await expect(
    card(page).getByRole("button", { name: "Kein Eingriff nötig", exact: true })
  ).toBeDisabled();
});

test("final confirmation rechecks fresh data and sends no switch after conditions change", async ({
  page,
}) => {
  await start(page);
  await review(page)
    .getByRole("button", {
      name: "Squad(s) informieren und wechseln",
      exact: true,
    })
    .click();
  const confirmation = page.getByRole("dialog", {
    name: "Koordinierter Squad-Wechsel",
    exact: true,
  });
  await expect(confirmation).toBeVisible();
  await changeSnapshot(page, "changed_squad");
  await confirmation
    .getByRole("button", { name: "Weiter", exact: true })
    .click();
  await confirmation
    .getByRole("button", { name: "Endgültig ausführen", exact: true })
    .click();
  await expect(
    confirmation.getByText(/Es wurde kein Wechsel ausgeführt/)
  ).toBeVisible();
  expect(
    await page.evaluate(() =>
      window.__CRCON_DEMO_PROTECTED_REQUESTS__.filter(
        (path) => path === "/api/execute_autobalancer_squad_switch"
      )
    )
  ).toEqual([]);
});

test("without an open review the proposal refreshes automatically after the hold period", async ({
  page,
}) => {
  await page.clock.install();
  await start(page);
  await review(page)
    .getByRole("button", { name: "Schließen", exact: true })
    .click();
  await changeSnapshot(page, "changed_squad");
  await page.clock.runFor(11_000);
  await expect(
    card(page)
      .getByRole("status")
      .filter({ hasText: "Vorschlag bitte aktualisieren" })
  ).toBeVisible();
  await page.clock.fastForward(60_000);
  await expect(
    card(page).getByText(/Auswahl bleibt bis zu 60 Sekunden sichtbar/)
  ).toBeVisible();
  await card(page)
    .getByRole("button", { name: "Squad-Wechsel prüfen", exact: true })
    .click();
  await expect(
    review(page).getByText("Squad delta", { exact: true })
  ).toBeVisible();
});

test("the refresh hint remains readable and actionable on mobile", async ({
  page,
}, testInfo) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await page.clock.install();
  await openDemoPage(page, "/views/live", {
    query: { demo_balance: "unbalanced" },
  });
  await expect(
    card(page).getByText(/Auswahl bleibt bis zu 60 Sekunden sichtbar/)
  ).toBeVisible();
  await changeSnapshot(page, "changed_squad");
  await page.clock.runFor(11_000);
  await expect(
    card(page)
      .getByRole("status")
      .filter({ hasText: "Vorschlag bitte aktualisieren" })
  ).toBeVisible();
  await expect(
    card(page).getByRole("button", { name: "Neu bewerten", exact: true })
  ).toBeEnabled();
  await expectNoHorizontalPageOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("proposal-refresh-mobile.png"),
    fullPage: true,
  });
  await card(page)
    .getByRole("button", { name: "Neu bewerten", exact: true })
    .click();
  await expect(
    card(page).getByText("Vorschlag zur Prüfung vorgemerkt", { exact: true })
  ).toBeVisible();
});

test("the teams view explains a no-longer-needed proposal too", async ({
  page,
}, testInfo) => {
  await page.clock.install();
  await openDemoPage(page, "/views/team", {
    query: { demo_balance: "unbalanced" },
  });
  await expect(
    card(page).getByText(/Auswahl bleibt bis zu 60 Sekunden sichtbar/)
  ).toBeVisible();
  await changeSnapshot(page, "balanced");
  await page.clock.runFor(11_000);
  const notice = card(page)
    .getByRole("status")
    .filter({ hasText: "Aktuell kein Wechsel nötig" });
  await expect(notice).toBeVisible();
  await expect(
    notice.getByRole("button", { name: "Neu bewerten", exact: true })
  ).toBeEnabled();
  await expectNoHorizontalPageOverflow(page);
  await notice.screenshot({
    path: testInfo.outputPath("proposal-balanced-desktop.png"),
  });
});

test("a still-valid review reaches the existing confirmed action exactly once", async ({
  page,
}) => {
  await start(page);
  await review(page)
    .getByRole("button", {
      name: "Squad(s) informieren und wechseln",
      exact: true,
    })
    .click();
  const confirmation = page.getByRole("dialog", {
    name: "Koordinierter Squad-Wechsel",
    exact: true,
  });
  await confirmation
    .getByRole("button", { name: "Weiter", exact: true })
    .click();
  await confirmation
    .getByRole("button", { name: "Endgültig ausführen", exact: true })
    .click();
  await expect(
    confirmation.getByText("Erfolgreich", { exact: true })
  ).toBeVisible();
  expect(
    await page.evaluate(() =>
      window.__CRCON_DEMO_PROTECTED_REQUESTS__.filter(
        (path) => path === "/api/execute_autobalancer_squad_switch"
      )
    )
  ).toHaveLength(1);
});
