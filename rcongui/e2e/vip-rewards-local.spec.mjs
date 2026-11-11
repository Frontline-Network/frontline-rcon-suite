import { test, expect } from "@playwright/test";
import { openDemoPage, expectNoHorizontalPageOverflow } from "./helpers.mjs";
const chooseRule = (page, name) =>
  page
    .getByRole("navigation", { name: "Belohnungsregeln" })
    .getByRole("button", { name: new RegExp(name) })
    .click();
const general = (page) =>
  page.getByRole("tab", { name: "Grundeinstellungen", exact: true }).click();
const rules = (page) =>
  page.getByRole("tab", { name: "Belohnungen", exact: true }).click();
const path = "/settings/others/vip-rewards";
test("local rewards form saves and discards without live requests", async ({
  page,
  baseURL,
}) => {
  const external = [];
  page.on("request", (r) => {
    if (
      /^https?:/.test(r.url()) &&
      new URL(r.url()).origin !== new URL(baseURL).origin
    )
      external.push(r.url());
  });
  await openDemoPage(page, path);
  await expect(
    page.getByRole("heading", { name: "VIP-Belohnungen", exact: true })
  ).toBeVisible();
  await expect(page.getByText(/Lokaler Formulartest/)).toBeVisible();
  await general(page);
  await expect(
    page.getByLabel("Vorschau: keine VIP-Vergabe und keine Spielernachrichten")
  ).toBeChecked();
  await general(page);
  const enabled = page.getByLabel("Neue VIP-Belohnungen aktivieren");
  await enabled.check();
  await page
    .getByRole("button", { name: "Einstellungen speichern", exact: true })
    .click();
  await expect(page.getByText(/Einstellungen gespeichert/)).toBeVisible();
  await enabled.uncheck();
  await page.getByRole("button", { name: "Änderungen verwerfen" }).click();
  await expect(enabled).toBeChecked();
  await page.screenshot({
    path: "../../outputs/next-release-local-20261111/form-desktop.png",
    fullPage: true,
  });
  expect(external).toEqual([]);
});
test("local rewards form fits mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openDemoPage(page, path);
  await expectNoHorizontalPageOverflow(page);
  await page.screenshot({
    path: "../../outputs/next-release-local-20261111/form-mobile.png",
    fullPage: true,
  });
});

test("rules reveal details and weapon choices survive save and reload reset", async ({
  page,
}) => {
  await openDemoPage(page, path);
  await chooseRule(page, "Nahkampf");
  const melee = page.getByLabel("Nahkampf aktivieren");
  await expect(
    page.getByRole("slider", {
      name: "Maximale Vergaben",
      exact: true,
    })
  ).toHaveCount(0);
  await melee.check();
  await expect(
    page.getByRole("slider", {
      name: "Maximale Vergaben",
      exact: true,
    })
  ).toBeVisible();
  await page
    .getByRole("slider", { name: "Maximale Vergaben", exact: true })
    .focus();
  await page.keyboard.press("Home");
  for (let i = 0; i < 5; i++) await page.keyboard.press("ArrowRight");
  await melee.uncheck();
  await expect(
    page.getByRole("slider", {
      name: "Maximale Vergaben",
      exact: true,
    })
  ).toHaveCount(0);
  await melee.check();
  await expect(
    page.getByRole("slider", {
      name: "Maximale Vergaben",
      exact: true,
    })
  ).toHaveAttribute("aria-valuetext", "6 Vergaben / Letzte 24 Stunden");
  await chooseRule(page, "Waffen-Challenges");
  await page
    .getByRole("button", { name: "Challenge hinzufügen", exact: true })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Waffen auswählen" })
  ).toHaveCount(0);
  await page.getByLabel("Aktiviert", { exact: true }).check();
  await page
    .getByRole("button", { name: "Einstellungen speichern", exact: true })
    .click();
  await expect(
    page.getByText(
      "Bitte wähle für jede aktive Waffen-Challenge mindestens eine Waffe aus."
    )
  ).toBeVisible();
  const weapons = page.getByRole("combobox", { name: "Waffen auswählen" });
  await weapons.fill("garand");
  await page.getByRole("option", { name: "M1 GARAND", exact: true }).click();
  await weapons.fill("mp40");
  await page.getByRole("option", { name: "MP40", exact: true }).click();
  await page.keyboard.press("Escape");
  await weapons.fill("");
  await page
    .getByRole("button", { name: "Einstellungen speichern", exact: true })
    .click();
  await expect(page.getByText(/Einstellungen gespeichert/)).toBeVisible();
  await expect(page.getByText("M1 GARAND", { exact: true })).toBeVisible();
  await expect(page.getByText("MP40", { exact: true })).toBeVisible();
  await page.reload();
  await chooseRule(page, "Nahkampf");
  await expect(page.getByLabel("Nahkampf aktivieren")).not.toBeChecked();
  await expect(
    page.getByRole("combobox", { name: "Waffen auswählen" })
  ).toHaveCount(0);
});

test("weekly support settings reveal on activation and save a custom command", async ({
  page,
}) => {
  await openDemoPage(page, path);
  await expect(page.getByLabel("Unterstützungspunkte pro Woche")).toHaveCount(
    0
  );
  await page.getByLabel("Wöchentliche Team-Unterstützung aktivieren").check();
  const points = page.getByRole("slider", {
    name: "Unterstützungspunkte pro Woche",
  });
  await points.focus();
  for (let i = 0; i < 30; i++) await page.keyboard.press("ArrowRight");
  const duration = page.getByRole("slider", {
    name: "VIP-Dauer (Tage)",
    exact: true,
  });
  await expect(duration).toHaveAttribute(
    "aria-valuetext",
    "0,25 Tage (6 Stunden)"
  );
  await duration.focus();
  await page.keyboard.press("ArrowRight");
  await general(page);
  await page
    .getByLabel("Chatbefehl für den Wochenfortschritt")
    .fill("!teamvip");
  await page
    .getByRole("button", { name: "Einstellungen speichern", exact: true })
    .click();
  await expect(page.getByText(/Einstellungen gespeichert/)).toBeVisible();
  await rules(page);
  await expect(
    page.getByLabel("Unterstützungspunkte pro Woche")
  ).toHaveAttribute("aria-valuetext", "8000");
  await expect(duration).toHaveAttribute(
    "aria-valuetext",
    "0,5 Tage (12 Stunden)"
  );
  const persisted = await page.evaluate(
    async () => (await (await fetch("/get_vip_rewards_config")).json()).result
  );
  expect(persisted.weekly_support.hours).toBe(12);
  await general(page);
  await expect(
    page.getByLabel("Chatbefehl für den Wochenfortschritt")
  ).toHaveValue("!teamvip");
  await rules(page);
  await page.getByLabel("Wöchentliche Team-Unterstützung aktivieren").uncheck();
  await expect(page.getByLabel("Unterstützungspunkte pro Woche")).toHaveCount(
    0
  );
  await page.getByRole("button", { name: "Änderungen verwerfen" }).click();
  await rules(page);
  await expect(
    page.getByLabel("Unterstützungspunkte pro Woche")
  ).toHaveAttribute("aria-valuetext", "8000");
  await page.setViewportSize({ width: 390, height: 844 });
  await expectNoHorizontalPageOverflow(page);
});

test("award period and threshold sliders persist", async ({ page }) => {
  await openDemoPage(page, path);
  await chooseRule(page, "Rundentreue");
  await page.getByLabel("Rundentreue aktivieren").check();
  await page.getByLabel("Zeitraum für maximale Vergaben").click();
  await page.getByRole("option", { name: "Monatlich", exact: true }).click();
  const minutes = page.getByRole("slider", {
    name: "Mindestspielzeit (Minuten)",
    exact: true,
  });
  await minutes.focus();
  await page.keyboard.press("ArrowRight");
  const share = page.getByRole("slider", {
    name: "Mindestanteil der Runde (%)",
    exact: true,
  });
  await share.focus();
  await page.keyboard.press("ArrowRight");
  await page
    .getByRole("button", { name: "Einstellungen speichern", exact: true })
    .click();
  await expect(page.getByText(/Einstellungen gespeichert/)).toBeVisible();
  const cfg = await page.evaluate(
    async () => (await (await fetch("/get_vip_rewards_config")).json()).result
  );
  expect(cfg.round.limit_period).toBe("month");
  expect(cfg.round.minutes).toBe(31);
  expect(cfg.round.fraction).toBe(0.71);
  await page.setViewportSize({ width: 390, height: 844 });
  await expectNoHorizontalPageOverflow(page);
});

test("excluded players and timezone are searchable selections", async ({
  page,
}) => {
  await openDemoPage(page, path);
  await general(page);
  const players = page.getByRole("combobox", {
    name: "Ausgeschlossene Spieler",
    exact: true,
  });
  await players.fill("Raven");
  await page.getByRole("option", { name: /FLN_Raven/ }).click();
  await players.fill("Wolf");
  await page.getByRole("option", { name: /FLN_Wolf/ }).click();
  const timezone = page.getByRole("combobox", {
    name: "Zeitzone",
    exact: true,
  });
  await timezone.fill("London");
  await page
    .getByRole("option", { name: "Europe/London", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Einstellungen speichern", exact: true })
    .click();
  await expect(page.getByText(/Einstellungen gespeichert/)).toBeVisible();
  const cfg = await page.evaluate(
    async () => (await (await fetch("/get_vip_rewards_config")).json()).result
  );
  expect(cfg.excluded_player_ids).toEqual([
    "76561198000000001",
    "76561198000000002",
  ]);
  expect(cfg.timezone).toBe("Europe/London");
  await players.focus();
  await page.keyboard.press("Backspace");
  await page.getByRole("button", { name: "Änderungen verwerfen" }).click();
  await expect(page.getByText("FLN_Wolf", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expectNoHorizontalPageOverflow(page);
});
