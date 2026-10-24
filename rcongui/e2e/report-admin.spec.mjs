import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  expectNoHorizontalPageOverflow,
  VIEWPORTS,
  collectRuntimeErrors,
} from "./helpers.mjs";

const titles = {
  de: "Report-Admin – Kommunikation, Teamkills & Cheatprüfung",
  en: "Report admin – communication, teamkills & cheat review",
};

async function openReportAdmin(page, language = "de", query = {}) {
  await openDemoPage(page, "/apps/discord-report-bot", {
    language,
    query: { demo_discord: "connected", ...query },
  });
  // Connected fixtures initially select Test after integration data arrives.
  // Wait for that initialization before choosing another step.
  await expect(page.getByTestId("discord-wizard-step-test")).toBeVisible();
  const wizard = page.getByRole("navigation", {
    name: language === "de" ? "Einrichtungsfortschritt Discord Report Bot" : "Discord Report Bot setup progress",
  });
  const label = language === "de" ? "KI & Report-Admin" : "AI & report admin";
  if (page.viewportSize().width < 600) {
    await wizard.getByRole("combobox").click();
    await page.getByRole("option", { name: `5. ${label}`, exact: true }).click();
  } else {
    await wizard.getByRole("button", { name: label, exact: true }).click();
  }
  await expect(page.getByTestId("discord-wizard-step-ai")).toBeVisible();
  return page.getByRole("region", { name: titles[language], exact: true });
}

test("report admin defaults to disabled dry run and explains real kick risks", async ({ page }) => {
  const errors = collectRuntimeErrors(page);
  const report = await openReportAdmin(page);
  await expect(report.getByLabel("Report-Admin aktivieren", { exact: true })).not.toBeChecked();
  await expect(report.getByLabel("Betriebsart", { exact: true })).toContainText("Probelauf – keine Kicks");
  await expect(report.getByLabel("Selbstmeldungen für Tests zulassen")).not.toBeChecked();
  await expect(report.getByLabel("Kommunikationsmeldungen auch gegen namentlich gemeldete Squadmitglieder")).not.toBeChecked();
  await expect(report).toContainText("Führungsabstimmungen wurden eingestellt");
  await expect(report).toContainText("Ob jemand tatsächlich spricht, ist technisch nicht überprüfbar");
  await report.getByLabel("Betriebsart", { exact: true }).click();
  await page.getByRole("option", { name: "Aktiv – automatische Kicks", exact: true }).click();
  await expect(report).toContainText("ohne Abstimmung oder Vorwarnung zum Kick");
  await report.getByLabel("Selbstmeldungen für Tests zulassen").check();
  await expect(report).toContainText("kann dies dich tatsächlich vom Server kicken");
  await expect(report.getByLabel("Report-Admin aktivieren", { exact: true })).not.toBeChecked();
  await expect(page.getByRole("region", { name: "Führungsabstimmung", exact: true })).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("report rules save the explicit member opt-in without enabling kicks or self-reports", async ({ page }) => {
  const report = await openReportAdmin(page);
  const members = report.getByLabel("Kommunikationsmeldungen auch gegen namentlich gemeldete Squadmitglieder");
  await members.check();
  await report.getByRole("combobox", { name: "Einordnung des Meldegrunds" }).click();
  await page.getByRole("option", { name: "KI – vollständigen Inhalt einordnen", exact: true }).click();
  await expect(report).toContainText("kein Suchwort-Fallback");
  await expect(report).toContainText("niemals den ganzen Squad");
  await expect(report).toContainText("60 Sekunden stiller Wartezeit");
  await expect(report).toContainText("Keine automatischen Cheat-Kicks oder Banns");
  await report.getByRole("button", { name: "Report-Regeln speichern" }).click();
  await expect(report.getByText("Gespeichert", { exact: true })).toBeVisible();
  const config = await page.evaluate(async () => (await (await fetch("/api/report-admin/v1/config")).json()).result.config);
  expect(config).toMatchObject({
    enabled: false, mode: "dry_run", reason_mode: "ai",
    communication_squad_members: true, allow_self_reports: false,
  });
  await expect(members).toBeChecked();
  await expectNoHorizontalPageOverflow(page);
});

test("English mobile report settings are explained and hidden from a viewer", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  const report = await openReportAdmin(page, "en");
  await expect(report).toBeVisible();
  await expect(report).toContainText("Leadership voting has been retired");
  await expect(report).toContainText("silent 60-second window");
  await expect(report).toContainText("No automatic cheat kicks or bans");
  await expect(report).toContainText("A squad name still reports only its leader, never the entire squad");
  await expect(report.getByLabel("Include explicitly named squad members in communication reports")).not.toBeChecked();
  await expectNoHorizontalPageOverflow(page);
  await openReportAdmin(page, "en", { demo_role: "viewer" });
  await expect(page.getByRole("region", { name: titles.en, exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Enable report admin", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Enable leadership voting", { exact: true })).toHaveCount(0);
});

test("report admin safety guidance follows theme presets and color-vision modes", async ({ page }) => {
  test.setTimeout(120_000);
  page.setDefaultTimeout(12_000);
  const errors = collectRuntimeErrors(page);
  await page.setViewportSize(VIEWPORTS.desktop);
  const report = await openReportAdmin(page);
  for (const [label, preset, colorVision, mode] of [
    ["Tactical Blue", "tactical-blue", "deuteranopia", "light"],
    ["Signal Green", "signal-green", "protanopia", "dark"],
    ["Command Red", "command-red", "tritanopia", "light"],
    ["Neutral", "neutral", "standard", "dark"],
    ["Vanguard Gold", "frontline-gold", "standard", "dark"],
  ]) {
    await page.locator('[data-testid="user-options-menu"]:visible').click();
    await page.getByRole("menuitem", { name: "Darstellung & Farben" }).click();
    const dialog = page.getByRole("dialog", { name: "Darstellung & Farben" });
    await dialog.getByRole("button", { name: label, exact: true }).click();
    await dialog.locator(`button[value="${mode}"]`).click();
    await dialog.locator(`input[type="radio"][value="${colorVision}"]`).check();
    await dialog.getByRole("button", { name: "Änderungen übernehmen" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.locator("html")).toHaveAttribute("data-theme-preset", preset);
    await expect(page.locator("html")).toHaveAttribute("data-color-vision", colorVision);
    await report.getByRole("heading", { name: titles.de, exact: true }).scrollIntoViewIfNeeded();
    await expect(report).toContainText("ohne Abstimmung oder Vorwarnung zum Kick");
    await expect(report.getByLabel("Report-Admin aktivieren", { exact: true })).not.toBeChecked();
    await expectNoHorizontalPageOverflow(page);
  }
  expect(errors).toEqual([]);
});
