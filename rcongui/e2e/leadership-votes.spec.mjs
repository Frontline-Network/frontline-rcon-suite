import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  expectNoHorizontalPageOverflow,
  VIEWPORTS,
  collectRuntimeErrors,
} from "./helpers.mjs";

test("commander target and explicit active-mode warning", async ({ page }) => {
  await openDemoPage(page, "/apps/discord-report-bot", {
    query: { demo_vote_target: "commander" },
    language: "de",
  });
  const section = page.getByRole("region", {
    name: "Führungsabstimmung",
    exact: true,
  });
  await expect(
    section.getByRole("heading", { name: "Führungsabstimmung · Commander" })
  ).toBeVisible();
  await expect(section.getByLabel("Betriebsmodus")).toContainText("Probelauf");
  await section.getByLabel("Betriebsmodus").click();
  await page
    .getByRole("option", {
      name: "Aktiv – automatischer Server-Kick",
      exact: true,
    })
    .click();
  await expect(
    section.getByText("Aktivmodus: Eine erfolgreiche Abstimmung", {
      exact: false,
    })
  ).toBeVisible();
  await expect(
    section.getByLabel("Führungsabstimmung aktivieren")
  ).not.toBeChecked();
});

test("leadership settings, fixed quorum, ballot details and cancellation", async ({
  page,
}) => {
  const errors = collectRuntimeErrors(page);
  await page.setViewportSize(VIEWPORTS.desktop);
  await openDemoPage(page, "/apps/discord-report-bot");
  const main = page.getByRole("region", {
    name: "Führungsabstimmung",
    exact: true,
  });
  await expect(
    main.getByRole("heading", { name: "Führungsabstimmung", exact: true })
  ).toBeVisible();
  await expect(
    main.getByLabel("Führungsabstimmung aktivieren")
  ).not.toBeChecked();
  await expect(
    main.getByText("bei 3 sind 2 Ja-Stimmen nötig, bei 6 sind es 4.", {
      exact: false,
    })
  ).toBeVisible();
  await main.getByLabel("Führungsabstimmung aktivieren").check();
  await main.getByRole("button", { name: "Einstellungen speichern" }).click();
  await expect(
    main.getByText("Einstellungen gespeichert", { exact: true })
  ).toBeVisible();
  await expect(
    main.getByText("Abstimmung läuft", { exact: true })
  ).toBeVisible();
  await main.getByText("Einzelne Stimmen", { exact: false }).click();
  await expect(
    main.getByText("Demo Führung 1: Ja", { exact: true })
  ).toBeVisible();
  await main.getByRole("button", { name: "Vote abbrechen" }).click();
  await expect(
    main.getByText("Abgebrochen – kein Kick", { exact: true })
  ).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
  await page.screenshot({
    path: "test-results/leadership-votes-desktop.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("English mobile layout and permission denial", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/apps/discord-report-bot", {
    language: "en",
  });
  await expect(
    page.getByRole("heading", { name: "Leadership vote", exact: true })
  ).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
  await page
    .getByRole("region", { name: "Leadership vote", exact: true })
    .scrollIntoViewIfNeeded();
  await page.screenshot({
    path: "test-results/leadership-votes-mobile.png",
    fullPage: true,
  });
  await openDemoPage(page, "/apps/discord-report-bot", {
    query: { demo_role: "viewer" },
    language: "en",
  });
  await expect(
    page.getByText(
      "You need leadership-vote management permission to view these settings.",
      { exact: true }
    )
  ).toBeVisible();
  await expect(page.getByLabel("Enable leadership voting")).toHaveCount(0);
});

test("vote panel follows theme presets and every color-vision mode", async ({
  page,
}) => {
  test.setTimeout(120_000);
  page.setDefaultTimeout(12_000);
  const errors = collectRuntimeErrors(page);
  await page.setViewportSize(VIEWPORTS.desktop);
  await openDemoPage(page, "/apps/discord-report-bot");
  const variants = [
    ["Tactical Blue", "tactical-blue", "deuteranopia", "light"],
    ["Signal Green", "signal-green", "protanopia", "dark"],
    ["Command Red", "command-red", "tritanopia", "light"],
    ["Neutral", "neutral", "standard", "dark"],
    ["Frontline Gold", "frontline-gold", "standard", "dark"],
  ];
  for (const [label, preset, colorVision, mode] of variants) {
    await page.locator('[data-testid="user-options-menu"]:visible').click();
    await page.getByRole("menuitem", { name: "Darstellung & Farben" }).click();
    const dialog = page.getByRole("dialog", { name: "Darstellung & Farben" });
    await dialog.getByRole("button", { name: label, exact: true }).click();
    await dialog.locator(`button[value="${mode}"]`).click();
    await dialog.locator(`input[type="radio"][value="${colorVision}"]`).check();
    await dialog.getByRole("button", { name: "Änderungen übernehmen" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.locator("html")).toHaveAttribute(
      "data-theme-preset",
      preset
    );
    await expect(page.locator("html")).toHaveAttribute(
      "data-color-vision",
      colorVision
    );
    const vote = page.getByRole("heading", {
      name: /Führungsabstimmung · Squad Able/,
    });
    await vote.scrollIntoViewIfNeeded();
    await expect(vote).toBeVisible();
    await expect(
      page.getByText("Mehrheit fehlt – Admins erforderlich", { exact: true })
    ).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
    await page.screenshot({
      path: `test-results/leadership-${preset}-${colorVision}.png`,
    });
  }
  expect(errors).toEqual([]);
});
