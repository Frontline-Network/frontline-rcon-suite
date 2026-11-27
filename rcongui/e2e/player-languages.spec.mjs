import { test, expect } from "@playwright/test";
import { openDemoPage, collectRuntimeErrors, expectNoHorizontalPageOverflow } from "./helpers.mjs";

test("language management can be opened from the moderation navigation", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await openDemoPage(page, "/");
  await page.getByTestId("desktop-command-rail").getByRole("button", { name: "Moderation", exact: true }).click();
  await page.getByTestId("desktop-navigation-panel").getByRole("link", { name: "Spielersprachen und Übersetzungen", exact: true }).click();
  await expect(page).toHaveURL(/\/settings\/player-languages$/);
  await expect(page.getByRole("heading", { name: "Spielersprachen und Übersetzungen", exact: true })).toBeVisible();
});

test("a viewer sees the language-management destination as permission protected", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await openDemoPage(page, "/", { query: { demo_role: "viewer" } });
  await page.getByTestId("desktop-command-rail").getByRole("button", { name: "Moderation", exact: true }).click();
  const panel=page.getByTestId("desktop-navigation-panel");
  await expect(panel.getByRole("button", { name: "Spielersprachen und Übersetzungen", exact: true })).toHaveAttribute("aria-disabled","true");
  await expect(panel.getByRole("link", { name: "Spielersprachen und Übersetzungen", exact: true })).toHaveCount(0);
});

for (const [language, heading, original] of [
  ["de", "Spielersprachen und Übersetzungen", "Originaltext"],
  ["en", "Player languages and translations", "Original text"],
  ["fr", "Langues des joueurs et traductions", "Texte original"],
]) {
  test(`language template management is localized in ${language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    await openDemoPage(page, "/settings/player-languages", { language });
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
    await expect(page.getByLabel(original, { exact: true }).first()).toHaveValue("Bitte beachte die Serverregeln.");
    await page.getByRole("tab", { name: "Français", exact: true }).click();
    await expect(page.getByRole("textbox", { name: /Traduction · fr|Translation · fr|Übersetzung · fr/ })).toHaveValue("Veuillez respecter les règles du serveur.");
    await expectNoHorizontalPageOverflow(page);
    await page.screenshot({ path: test.info().outputPath("language-templates.png"), fullPage: true });
    expect(errors).toEqual([]);
  });
}

test("translations save and a selected player language drives a message-free preview", async ({ page }) => {
  const commands = [];
  page.on("request", request => { if (request.method() === "POST") commands.push(new URL(request.url()).pathname); });
  await openDemoPage(page, "/settings/player-languages");
  await page.getByRole("tab", { name: "English", exact: true }).click();
  await page.getByLabel("Übersetzung · en", { exact: true }).fill("Please respect our squad rules.");
  await page.getByRole("button", { name: "Übersetzungen speichern", exact: true }).click();
  await expect(page.getByText("Gespeichert", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Neu laden", exact: true }).click();
  await expect(page.getByLabel("Übersetzung · en", { exact: true })).toHaveValue("Please respect our squad rules.");
  await page.getByLabel("Spieler-ID", { exact: true }).first().fill("00020000000000000000000000000001");
  await page.getByRole("button", { name: "Sprachprofil öffnen", exact: true }).click();
  const profile = page.getByTestId("player-language-profile");
  await profile.getByRole("combobox", { name: /^Spielersprache/ }).click();
  await page.getByRole("option", { name: "English", exact: true }).click();
  await profile.getByRole("button", { name: "Sprache speichern", exact: true }).click();
  await expect(profile.getByText("Ausdrücklich gewählt", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Versandvorschau", exact: true }).click();
  await expect(page.getByTestId("localized-preview")).toContainText("Please respect our squad rules.");
  expect(commands.some(command => /\/(?:kick|punish|temp_ban|perma_ban|message_player)$/.test(command))).toBe(false);
});

test("a placeholder mismatch is visible and cannot silently overwrite a translation", async ({ page }) => {
  await openDemoPage(page, "/settings/player-languages");
  await page.getByRole("combobox", { name: /^Vorlage/ }).click();
  await page.getByRole("option", { name: "automod.no_leader.warning", exact: true }).click();
  await page.getByRole("tab", { name: "English", exact: true }).click();
  await page.getByLabel("Übersetzung · en", { exact: true }).fill("A placeholder is missing.");
  await page.getByRole("button", { name: "Übersetzungen speichern", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Every translation must preserve" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Übersetzungen speichern", exact: true })).toBeEnabled();
});

test("switching templates protects an unsaved translation", async ({ page }) => {
  await openDemoPage(page, "/settings/player-languages");
  await page.getByLabel("Übersetzung · de", { exact: true }).fill("Nicht gespeicherte Änderung");
  await page.getByRole("combobox", { name: /^Vorlage/ }).click();
  await page.getByRole("option", { name: "autobalancer.disabled", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Nicht gespeicherte Übersetzungen");
  await dialog.getByRole("button", { name: "Zurück", exact: true }).click();
  await expect(page.getByLabel("Übersetzung · de", { exact: true })).toHaveValue("Nicht gespeicherte Änderung");
});

test("language management fits a console player's phone-sized viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openDemoPage(page, "/settings/player-languages");
  await expect(page.getByRole("heading", { name: "Spielersprachen und Übersetzungen", exact: true })).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
});
