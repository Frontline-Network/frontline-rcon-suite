import { expect, test } from "@playwright/test";
import { collectRuntimeErrors, openDemoPage } from "./helpers.mjs";

for (const sample of [
  { language: "de", title: "Spielersitzungen: Ereignisse prüfen", link: "Mit Sitzung 12 verknüpfen", unknown: "Unbekannte Spielerkennung", discard: "Ereignis verwerfen" },
  { language: "en", title: "Player sessions: review events", link: "Link to session 12", unknown: "Unknown player identity", discard: "Discard event" },
  { language: "fr", title: "Sessions des joueurs : vérifier les événements", link: "Associer à la session 12", unknown: "Identité du joueur inconnue", discard: "Ignorer l’événement" },
]) {
  test(`session event review is authorized and usable in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_session_review: 1 },
    });
    const panel = main.getByTestId("session-event-review");
    await expect(panel.getByText(sample.title)).toBeVisible();
    await expect(panel.getByText(/fake-console-id/)).toBeVisible();
    page.on("dialog", async (dialog) => {
      if (dialog.type() === "prompt") await dialog.accept("Server logs checked");
      else await dialog.accept();
    });
    await panel.getByRole("button", { name: sample.link }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
  test(`unidentified events can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/players", {
      language: sample.language, query: { demo_session_review: 1, anonymous: 1 },
    });
    const panel = main.getByTestId("session-event-review");
    await expect(panel.getByText(sample.unknown)).toBeVisible();
    await expect(panel.getByText(/DISCONNECTED \(\)/)).toBeVisible();
    page.on("dialog", async (dialog) => dialog.accept(dialog.type() === "prompt" ? "Verified anonymous event" : undefined));
    await panel.getByRole("button", { name: sample.discard }).click();
    await expect(panel).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}
