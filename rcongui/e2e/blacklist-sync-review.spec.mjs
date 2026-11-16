import { expect, test } from "@playwright/test";
import { collectRuntimeErrors, openDemoPage } from "./helpers.mjs";

for (const sample of [
  { language: "de", title: "Sperrlisten-Synchronisation: Prüfung erforderlich", details: "Einzelheiten", confirm: "Als geprüft markieren", empty: "Keine offenen Prüfungen.", ownership: "Die Herkunft des Spielserver-Bans ist nicht eindeutig.", identity: "Die Steam- und EOS-ID konnten nicht eindeutig zugeordnet werden." },
  { language: "en", title: "Blacklist synchronization: review required", details: "Details", confirm: "Mark as reviewed", empty: "No outstanding reviews.", ownership: "The game-server ban's origin is unclear.", identity: "The Steam and EOS IDs could not be linked with confidence." },
  { language: "fr", title: "Synchronisation des listes noires : vérification requise", details: "Détails", confirm: "Marquer comme vérifié", empty: "Aucune vérification en attente.", ownership: "L’origine du bannissement sur le serveur de jeu est incertaine.", identity: "Les identifiants Steam et EOS n’ont pas pu être associés avec certitude." },
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
  for (const kind of ["ownership", "identity"]) {
    test(`blacklist review explains ${kind} in ${sample.language}`, async ({ page }) => {
      const errors = collectRuntimeErrors(page);
      const main = await openDemoPage(page, "/records/blacklists/manage", {
        language: sample.language, query: { demo_blacklist_review: kind },
      });
      await expect(main.getByTestId("blacklist-sync-review").getByText(sample[kind], { exact: false })).toBeVisible();
      expect(errors).toEqual([]);
    });
  }
}
