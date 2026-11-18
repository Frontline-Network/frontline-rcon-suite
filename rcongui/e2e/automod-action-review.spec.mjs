import { expect, test } from "@playwright/test";
import { collectRuntimeErrors, openDemoPage } from "./helpers.mjs";

for (const sample of [
  { language: "de", title: "Unbestätigte automatische Aktionen", release: "Nach Prüfung freigeben", all: "Alle Spieler dieser Regel", rule: "Squad ohne Anführer", warning: "Warnung", teamkill: "Teamkill nach Verbindung", ban: "Sperre", switchRule: "Autobalancer-Teamwechsel", switchAction: "Teamwechsel" },
  { language: "en", title: "Unconfirmed automatic actions", release: "Release after review", all: "All players for this rule", rule: "Squad without leader", warning: "Warning", teamkill: "Teamkill after connection", ban: "Ban", switchRule: "Autobalancer team switch", switchAction: "Team switch" },
  { language: "fr", title: "Actions automatiques non confirmées", release: "Débloquer après vérification", all: "Tous les joueurs concernés par cette règle", rule: "Escouade sans chef", warning: "Avertissement", teamkill: "Élimination alliée après connexion", ban: "Bannissement", switchRule: "Changement d’équipe par l’équilibrage", switchAction: "Changement d’équipe" },
]) {
  test(`uncertain automod actions can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1 },
    });
    await main.getByRole("button", { name: { de: "Automatische Aktionen verwalten", en: "Manage automatic actions", fr: "Gérer les actions automatiques" }[sample.language] }).click();
    const panel = main.getByTestId("automod-action-review");
    await expect(panel.getByText(sample.title)).toBeVisible();
    await expect(panel.getByText(/fake-console-id/)).toBeVisible();
    await expect(panel.getByText(new RegExp(`${sample.rule}.*${sample.warning}`))).toBeVisible();
    page.on("dialog", async (dialog) => dialog.accept(dialog.type() === "prompt" ? "Verified server logs" : undefined));
    await panel.getByRole("button", { name: sample.release }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
  test(`legacy rule-wide holds are identifiable in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1, global_hold: 1 },
    });
    await main.getByRole("button", { name: { de: "Automatische Aktionen verwalten", en: "Manage automatic actions", fr: "Gérer les actions automatiques" }[sample.language] }).click();
    const panel = main.getByTestId("automod-action-review");
    await expect(panel.getByText(sample.all)).toBeVisible();
    await expect(panel.getByRole("button", { name: sample.release })).toBeVisible();
    expect(errors).toEqual([]);
  });
  test(`teamkill ban holds can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1, teamkill_hold: 1 },
    });
    await main.getByRole("button", { name: { de: "Automatische Aktionen verwalten", en: "Manage automatic actions", fr: "Gérer les actions automatiques" }[sample.language] }).click();
    const panel = main.getByTestId("automod-action-review");
    await expect(panel.getByText(new RegExp(`${sample.teamkill}.*${sample.ban}`))).toBeVisible();
    page.on("dialog", async (dialog) => dialog.accept(dialog.type() === "prompt" ? "Verified server logs" : undefined));
    await panel.getByRole("button", { name: sample.release }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
  test(`uncertain team switches can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1, switch_hold: 1 },
    });
    await main.getByRole("button", { name: { de: "Automatische Aktionen verwalten", en: "Manage automatic actions", fr: "Gérer les actions automatiques" }[sample.language] }).click();
    const panel = main.getByTestId("automod-action-review");
    await expect(panel.getByText(new RegExp(`${sample.switchRule}.*${sample.switchAction}`))).toBeVisible();
    page.on("dialog", async (dialog) => dialog.accept(dialog.type() === "prompt" ? "Verified server logs" : undefined));
    await panel.getByRole("button", { name: sample.release }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
  test(`uncertain name kicks can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1, name_kick_hold: 1, global_hold: 1 },
    });
    await main.getByRole("button", { name: { de: "Automatische Aktionen verwalten", en: "Manage automatic actions", fr: "Gérer les actions automatiques" }[sample.language] }).click();
    const panel = main.getByTestId("automod-action-review");
    const label = { de: "Namensfilter", en: "Name filter", fr: "Filtre des noms" }[sample.language];
    await expect(panel.getByText(new RegExp(label))).toBeVisible();
    await expect(panel.getByText(sample.all)).toBeVisible();
    page.on("dialog", async (dialog) => dialog.accept(dialog.type() === "prompt" ? "Verified server logs" : undefined));
    await panel.getByRole("button", { name: sample.release }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
  test(`uncertain VAC bans can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1, vac_hold: 1, global_hold: 1 },
    });
    await main.getByRole("button", { name: { de: "Automatische Aktionen verwalten", en: "Manage automatic actions", fr: "Gérer les actions automatiques" }[sample.language] }).click();
    const panel = main.getByTestId("automod-action-review");
    const label = { de: "VAC-Vorgeschichte", en: "VAC history", fr: "Antécédents VAC" }[sample.language];
    await expect(panel.getByText(new RegExp(label))).toBeVisible();
    await expect(panel.getByText(sample.all)).toBeVisible();
    page.on("dialog", async (dialog) => dialog.accept(dialog.type() === "prompt" ? "Verified server logs" : undefined));
    await panel.getByRole("button", { name: sample.release }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
  test(`uncertain Windows Store actions can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1, windows_store_hold: 1, global_hold: 1 },
    });
    await main.getByRole("button", { name: { de: "Automatische Aktionen verwalten", en: "Manage automatic actions", fr: "Gérer les actions automatiques" }[sample.language] }).click();
    const panel = main.getByTestId("automod-action-review");
    const label = { de: "Windows-Store-Regel", en: "Windows Store rule", fr: "Règle Windows Store" }[sample.language];
    await expect(panel.getByText(new RegExp(label))).toBeVisible();
    await expect(panel.getByText(sample.all)).toBeVisible();
    page.on("dialog", async (dialog) => dialog.accept(dialog.type() === "prompt" ? "Verified server logs" : undefined));
    await panel.getByRole("button", { name: sample.release }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
  test(`uncertain blacklist actions can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1, blacklist_action_hold: 1, global_hold: 1 },
    });
    await main.getByRole("button", { name: { de: "Automatische Aktionen verwalten", en: "Manage automatic actions", fr: "Gérer les actions automatiques" }[sample.language] }).click();
    const panel = main.getByTestId("automod-action-review");
    const label = { de: "Sperrlisten-Durchsetzung", en: "Blacklist enforcement", fr: "Application des listes de blocage" }[sample.language];
    await expect(panel.getByText(new RegExp(label))).toBeVisible();
    await expect(panel.getByText(sample.all)).toBeVisible();
    page.on("dialog", async (dialog) => dialog.accept(dialog.type() === "prompt" ? "Verified server logs" : undefined));
    await panel.getByRole("button", { name: sample.release }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
  test(`uncertain Vietnam VIP restores can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1, vip_restore_hold: 1 },
    });
    await main.getByRole("button", { name: { de: "Automatische Aktionen verwalten", en: "Manage automatic actions", fr: "Gérer les actions automatiques" }[sample.language] }).click();
    const panel = main.getByTestId("automod-action-review");
    const label = { de: "Vietnam-VIP-Wiederherstellung", en: "Vietnam VIP restoration", fr: "Rétablissement VIP Vietnam" }[sample.language];
    await expect(panel.getByText(new RegExp(label))).toBeVisible();
    page.on("dialog", async dialog => dialog.accept(dialog.type() === "prompt" ? "Verified VIP state" : undefined));
    await panel.getByRole("button", { name: sample.release }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}
