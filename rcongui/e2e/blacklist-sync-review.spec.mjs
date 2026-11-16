import { expect, test } from "@playwright/test";
import { collectRuntimeErrors, openDemoPage } from "./helpers.mjs";

for (const sample of [
  { language: "de", title: "Sperrlisten-Synchronisation: Prüfung erforderlich", details: "Einzelheiten", confirm: "Als geprüft markieren", empty: "Keine offenen Prüfungen." },
  { language: "en", title: "Blacklist synchronization: review required", details: "Details", confirm: "Mark as reviewed", empty: "No outstanding reviews." },
  { language: "fr", title: "Synchronisation des listes noires : vérification requise", details: "Détails", confirm: "Marquer comme vérifié", empty: "Aucune vérification en attente." },
]) {
  test(`blacklist synchronization review is visible and acknowledged in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/blacklists/manage", {
      language: sample.language, query: { demo_blacklist_review: 1 },
    });
    const panel = main.getByTestId("blacklist-sync-review");
    await expect(panel.getByText(sample.title)).toBeVisible();
    await panel.getByText(sample.details, { exact: true }).click();
    await expect(panel.getByText(/fake-console-id/)).toBeVisible();
    page.once("dialog", (dialog) => dialog.accept());
    await panel.getByRole("button", { name: sample.confirm }).click();
    await expect(panel.getByText(sample.empty)).toBeVisible();
    expect(errors).toEqual([]);
  });
}
