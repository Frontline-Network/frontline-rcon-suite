import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.use({ viewport: VIEWPORTS.desktop });

test("English tactical map translates German evidence and retains its document language after reload", async ({
  page,
}) => {
  const context = [
    "Waffen, Rollen, Fahrzeuge, Spawnkämpfe und gemeinsame Frontabschnitte prüfen.",
    "Der Hinweis ist keine Cheat-Wahrscheinlichkeit und löst keine automatische Maßnahme aus.",
  ];
  let fixtureResponses = 0;

  // Tactical fake mode calls its fixture directly instead of the HTTP API.
  // Inject backend-shaped evidence into that fixture only. This exercises the
  // production DetectionPanel translation boundary, not production HTTP errors.
  // Do not replace any renderer, translation function or application logic.
  await page.route(
    /\/(?:assets\/demo-[^/]+|src\/pages\/views\/live-map\/demo)\.js(?:\?.*)?$/,
    async (route) => {
      const response = await route.fetch();
      const body = await response.text();
      if (!body.includes("demo-detection") || !body.includes("demoRequest")) {
        await route.fulfill({ response });
        return;
      }
      const fixtureField = /evidence\s*:\s*\{\s*signals\s*:/g;
      expect(
        [...body.matchAll(fixtureField)],
        "one unambiguous tactical evidence fixture"
      ).toHaveLength(1);
      fixtureResponses += 1;
      await route.fulfill({
        response,
        body: body.replace(
          fixtureField,
          `evidence:{context:${JSON.stringify(context)},signals:`
        ),
      });
    }
  );

  await openDemoPage(page, "/views/live-map", { language: "en" });
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  const view = page.getByTestId("live-map-page");
  await expect(view.getByTestId("player-map-marker")).toHaveCount(100);
  await expect(
    view.getByRole("group", { name: "Tactical map with selectable players" })
  ).toBeVisible();
  await expect(
    view.getByRole("button", { name: "Zoom in", exact: true })
  ).toBeVisible();
  await expect(view.getByLabel("Find player", { exact: true })).toBeVisible();
  await view
    .getByRole("button", { name: "Details & context", exact: true })
    .click();
  await expect(
    view.getByText(
      "Review weapons, roles, vehicles, fighting near spawn points and shared front-line areas.",
      { exact: true }
    )
  ).toBeVisible();
  await expect(
    view.getByText(
      "This hint is not a probability of cheating and does not trigger automatic action.",
      { exact: true }
    )
  ).toBeVisible();
  for (const original of context)
    await expect(view.getByText(original, { exact: true })).toHaveCount(0);
  // Fixture player names are user data, not UI translation keys.
  await expect(
    view.getByText("Demo Spieler 03", { exact: true }).first()
  ).toBeVisible();
  expect(fixtureResponses).toBe(1);

  await page.reload();
  await expect(page.getByTestId("live-map-page")).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(view.getByLabel("Find player", { exact: true })).toBeVisible();
  expect(fixtureResponses).toBe(2);
});
