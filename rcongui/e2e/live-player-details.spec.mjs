import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.describe("live player density and details", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("keeps every closed player on one line and opens one detail strip", async ({
    page,
  }) => {
    await openDemoPage(page, "/views/live");

    const panel = page.getByTestId("live-players-panel");
    const playerRows = panel.locator('tr[data-player-row="true"]');
    await expect.poll(() => playerRows.count()).toBeGreaterThan(1);

    const rowsToMeasure = Math.min(await playerRows.count(), 5);
    for (let index = 0; index < rowsToMeasure; index += 1) {
      const box = await playerRows.nth(index).boundingBox();
      expect(box?.height).toBeLessThanOrEqual(40);
    }

    const disclosureButtons = panel.getByRole("button", {
      name: /Details zu .* anzeigen/,
    });
    await disclosureButtons.first().click();
    await expect(panel.getByTestId("live-player-detail-panel")).toHaveCount(1);

    const nextDisclosure = panel
      .getByRole("button", { name: /Details zu .* anzeigen/ })
      .first();
    await nextDisclosure.click();
    await expect(panel.getByTestId("live-player-detail-panel")).toHaveCount(1);

    await panel
      .getByRole("button", { name: /Details zu .* schließen/ })
      .click();
    await expect(panel.getByTestId("live-player-detail-panel")).toHaveCount(0);
  });
});
