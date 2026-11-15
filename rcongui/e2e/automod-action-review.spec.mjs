import { expect, test } from "@playwright/test";
import { collectRuntimeErrors, openDemoPage } from "./helpers.mjs";

for (const sample of [
  { language: "de", title: "Unbestätigte Automod-Aktionen", release: "Nach Prüfung freigeben", all: "Alle Spieler dieser Regel", rule: "Squad ohne Anführer", warning: "Warnung" },
  { language: "en", title: "Unconfirmed automod actions", release: "Release after review", all: "All players for this rule", rule: "Squad without leader", warning: "Warning" },
  { language: "fr", title: "Actions Automod non confirmées", release: "Débloquer après vérification", all: "Tous les joueurs concernés par cette règle", rule: "Escouade sans chef", warning: "Avertissement" },
]) {
  test(`uncertain automod actions can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_automod_action_review: 1 },
    });
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
    const panel = main.getByTestId("automod-action-review");
    await expect(panel.getByText(sample.all)).toBeVisible();
    await expect(panel.getByRole("button", { name: sample.release })).toBeVisible();
    expect(errors).toEqual([]);
  });
}
