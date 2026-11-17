import { expect, test } from "@playwright/test";
import { collectRuntimeErrors, openDemoPage } from "./helpers.mjs";

for (const sample of [
  { language: "de", title: "Barricade-Scans prüfen", disabled: "Der neue automatische Scan ist deaktiviert.", cause: "Der Sitzungsbeginn liegt in der Aktivierungssekunde.", before: "Die Sitzung begann vor der Aktivierung.", decision: "Entscheidung", retry: "Erneuten Scan freigeben", warning: "Ein erneuter Scan kann eine doppelte Barricade-Meldung auslösen.", reason: "Begründung", save: "Entscheidung speichern", empty: "Keine offenen Scans." },
  { language: "en", title: "Review Barricade scans", disabled: "The new automatic scanner is disabled.", cause: "The session started during the activation second.", before: "The session started before activation.", decision: "Decision", retry: "Authorize another scan", warning: "Another scan may create a duplicate Barricade alert.", reason: "Reason", save: "Save decision", empty: "No scans need review." },
  { language: "fr", title: "Vérifier les analyses Barricade", disabled: "La nouvelle analyse automatique est désactivée.", cause: "La session a commencé pendant la seconde d’activation.", before: "La session a commencé avant l’activation.", decision: "Décision", retry: "Autoriser une nouvelle analyse", warning: "Une nouvelle analyse peut créer une alerte Barricade en double.", reason: "Motif", save: "Enregistrer la décision", empty: "Aucune analyse à vérifier." },
]) {
  test(`requires a reason and warns before scan retry in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/blacklists/manage", { language: sample.language, query: { demo_barricade_review: 1, demo_barricade_cause: "activation_ambiguous" } });
    const panel = main.getByTestId("barricade-scan-review");
    await expect(panel.getByText(sample.title)).toBeVisible();
    await expect(panel.getByText(sample.disabled)).toBeVisible();
    await expect(panel.getByText("synthetic-eos", { exact: false })).toBeVisible();
    await expect(panel.getByText(sample.cause, { exact: false })).toBeVisible();
    const save = panel.getByRole("button", { name: sample.save });
    await expect(save).toBeDisabled();
    await panel.getByRole("combobox", { name: sample.decision }).click();
    await page.getByRole("option", { name: sample.retry }).click();
    await expect(panel.getByText(sample.warning, { exact: false })).toBeVisible();
    await expect(save).toBeDisabled();
    await panel.getByLabel(sample.reason).fill("Synthetic review");
    await save.click();
    await expect(panel.getByText(sample.empty)).toBeVisible();
    expect(errors).toEqual([]);
  });
  test(`explains previous-session review in ${sample.language}`, async ({ page }) => {
    const main = await openDemoPage(page, "/records/blacklists/manage", { language: sample.language,
      query: { demo_barricade_review: 1, demo_barricade_cause: "activation_before" } });
    await expect(main.getByTestId("barricade-scan-review").getByText(sample.before, { exact: false })).toBeVisible();
  });
  test(`does not offer automatic retry for ended session in ${sample.language}`, async ({ page }) => {
    const main = await openDemoPage(page, "/records/blacklists/manage", { language: sample.language,
      query: { demo_barricade_review: 1, demo_barricade_cause: "session_ended_before_scan" } });
    const panel = main.getByTestId("barricade-scan-review");
    await panel.getByRole("combobox", { name: sample.decision }).click();
    await expect(page.getByRole("option", { name: sample.retry })).toHaveCount(0);
  });
}
