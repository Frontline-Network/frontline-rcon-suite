import { expect, test } from "@playwright/test";
import { collectRuntimeErrors, openDemoPage } from "./helpers.mjs";

for (const sample of [
  { language: "de", empty: "Es stehen keine Sitzungsereignisse zur Prüfung aus.", title: "Spielersitzungen: Ereignisse prüfen", link: "Mit Sitzung 12 verknüpfen", unknown: "Unbekannte Spielerkennung", discard: "Ereignis verwerfen" },
  { language: "en", empty: "There are no session events to review.", title: "Player sessions: review events", link: "Link to session 12", unknown: "Unknown player identity", discard: "Discard event" },
  { language: "fr", empty: "Aucun événement de session à vérifier.", title: "Sessions des joueurs : vérifier les événements", link: "Associer à la session 12", unknown: "Identité du joueur inconnue", discard: "Ignorer l’événement" },
]) {
  test(`session event review is authorized and usable in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/session-events", {
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
    await expect(panel.getByText(sample.empty)).toBeVisible();
    expect(errors).toEqual([]);
  });
  test(`unidentified events can be reviewed in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, "/records/session-events", {
      language: sample.language, query: { demo_session_review: 1, anonymous: 1 },
    });
    const panel = main.getByTestId("session-event-review");
    await expect(panel.getByText(sample.unknown)).toBeVisible();
    await expect(panel.getByText(/DISCONNECTED \(\)/)).toBeVisible();
    page.on("dialog", async (dialog) => dialog.accept(dialog.type() === "prompt" ? "Verified anonymous event" : undefined));
    await panel.getByRole("button", { name: sample.discard }).click();
    await expect(panel.getByText(sample.empty)).toBeVisible();
    expect(errors).toEqual([]);
  });
}

test("player records stay clear of pending session events", async ({ page }) => {
  const main = await openDemoPage(page, "/records/players", { query: { demo_session_review: 1 } });
  await expect(main.locator("#players-section")).toBeVisible();
  await expect(main.getByTestId("session-event-review")).toHaveCount(0);
});
