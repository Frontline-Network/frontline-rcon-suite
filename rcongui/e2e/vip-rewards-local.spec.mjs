import { test, expect } from "@playwright/test";
import { openDemoPage, expectNoHorizontalPageOverflow } from "./helpers.mjs";
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
  await expect(
    page.getByLabel("Vorschau: keine VIP-Vergabe und keine Spielernachrichten")
  ).toBeChecked();
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
  const melee = page.getByLabel("Nahkampf aktivieren");
  await expect(
    page.getByLabel("Max. Vergaben / 24 h", { exact: true })
  ).toHaveCount(0);
  await melee.check();
  await expect(
    page.getByLabel("Max. Vergaben / 24 h", { exact: true })
  ).toBeVisible();
  await page.getByLabel("Max. Vergaben / 24 h", { exact: true }).fill("6");
  await melee.uncheck();
  await expect(
    page.getByLabel("Max. Vergaben / 24 h", { exact: true })
  ).toHaveCount(0);
  await melee.check();
  await expect(
    page.getByLabel("Max. Vergaben / 24 h", { exact: true })
  ).toHaveValue("6");
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
  await page.getByLabel("Unterstützungspunkte pro Woche").fill("8000");
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
  await page
    .getByLabel("Chatbefehl für den Wochenfortschritt")
    .fill("!teamvip");
  await page
    .getByRole("button", { name: "Einstellungen speichern", exact: true })
    .click();
  await expect(page.getByText(/Einstellungen gespeichert/)).toBeVisible();
  await expect(page.getByLabel("Unterstützungspunkte pro Woche")).toHaveValue(
    "8000"
  );
  await expect(duration).toHaveAttribute(
    "aria-valuetext",
    "0,5 Tage (12 Stunden)"
  );
  const persisted = await page.evaluate(
    async () =>
      (
        await (await fetch("/get_vip_rewards_config")).json()
      ).result
  );
  expect(persisted.weekly_support.hours).toBe(12);
  await expect(
    page.getByLabel("Chatbefehl für den Wochenfortschritt")
  ).toHaveValue("!teamvip");
  await page.getByLabel("Wöchentliche Team-Unterstützung aktivieren").uncheck();
  await expect(page.getByLabel("Unterstützungspunkte pro Woche")).toHaveCount(
    0
  );
  await page.getByRole("button", { name: "Änderungen verwerfen" }).click();
  await expect(page.getByLabel("Unterstützungspunkte pro Woche")).toHaveValue(
    "8000"
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await expectNoHorizontalPageOverflow(page);
});
