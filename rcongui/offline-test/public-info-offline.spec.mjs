import { expect, test } from "@playwright/test";

for (const sample of [
  { language: "en", text: "The game server is currently unavailable. Please try again later." },
  { language: "de", text: "Der Spielserver ist derzeit nicht erreichbar. Bitte versuche es später erneut." },
  { language: "fr", text: "Le serveur de jeu est actuellement indisponible. Veuillez réessayer plus tard." },
]) {
  test(`public overview reports offline and recovers in ${sample.language}`, async ({ page }) => {
    let offline = true;
    await page.route("**/api/get_public_info", async route => {
      await route.fulfill(offline
        ? { status: 503, json: { failed: true, error: "game_server_unavailable", result: null } }
        : { status: 200, json: { failed: false, result: { player_count: 0 } } });
    });
    await page.goto("/e2e/fixtures/public-info-offline-harness.html");
    await page.evaluate(async language => {
      const harness = await import("/e2e/fixtures/public-info-offline-harness.jsx");
      await harness.showOverview(language);
    }, sample.language);
    const root = page.locator("#offline-test-root");
    await expect(root.getByText(sample.text)).toBeVisible();
    await expect(root.getByText("503", { exact: true })).toBeVisible();
    offline = false;
    await root.getByRole("link").click();
    await expect(root.getByTestId("overview-loaded")).toBeVisible();
  });
}
