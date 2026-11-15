import { expect, test } from "@playwright/test";
import { collectRuntimeErrors, openDemoPage } from "./helpers.mjs";

for (const sample of [
  { language: "de", reward: /^VIP-Belohnung/, title: "Seed-VIP: Prüfung erforderlich", confirm: "Als geprüft markieren", empty: "Keine offenen Prüfungen." },
  { language: "en", reward: /^VIP reward/i, title: "Seed VIP: review required", confirm: "Mark as reviewed", empty: "No outstanding reviews." },
  { language: "fr", reward: /^Récompense VIP/i, title: "Seed VIP : vérification requise", confirm: "Marquer comme vérifié", empty: "Aucune vérification en attente." },
]) {
  test(`seed VIP review is visible and can be acknowledged in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/settings/others/seed-vip", {
      language: sample.language,
      query: { demo_seed_review: 1 },
    });
    await main.getByRole("navigation").getByRole("button", { name: sample.reward }).click();
    const panel = main.getByTestId("seed-vip-review-journal");
    await expect(panel.getByText(sample.title)).toBeVisible();
    await expect(panel.getByText(/Example Player/)).toBeVisible();
    page.once("dialog", (dialog) => dialog.accept());
    await panel.getByRole("button", { name: sample.confirm }).click();
    await expect(panel.getByText(sample.empty)).toBeVisible();
    expect(errors).toEqual([]);
  });
}
