import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.describe("shared player action menus", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("opens one shared menu from a team player row", async ({ page }) => {
    await openDemoPage(page, "/views/team");

    await page
      .getByRole("button", { name: /Trupp .* öffnen/i })
      .first()
      .click();
    await page.getByTestId("team-player-action-trigger").first().click();

    const menu = page.locator("#team-player-row-actions-menu:visible");
    await expect(menu).toHaveCount(1);
    await expect(menu.getByRole("menuitem").first()).toBeVisible();
    await expect(page.locator("#team-player-row-actions-menu")).toHaveCount(1);
  });

  test("opens one shared menu from a live-session player row", async ({
    page,
  }) => {
    await openDemoPage(page, "/stats/live-sessions");

    const expandableRow = page.locator("table button[aria-expanded]").first();
    await expect(expandableRow).toBeVisible();
    await expandableRow.click();

    const actionTrigger = page.getByTestId(
      "live-sessions-player-action-trigger"
    );
    await actionTrigger.first().click();

    const menu = page.locator("#live-sessions-player-actions-menu:visible");
    await expect(menu).toHaveCount(1);
    await expect(menu.getByRole("menuitem").first()).toBeVisible();
    await expect(
      page.locator("#live-sessions-player-actions-menu")
    ).toHaveCount(1);
  });
});

test.describe("shared player action menu on mobile", () => {
  test.use({ viewport: VIEWPORTS.mobile });

  test("reuses the live-session menu for mobile player cards", async ({
    page,
  }) => {
    await openDemoPage(page, "/stats/live-sessions");

    const expandableUnit = page
      .locator('#main-content button[aria-expanded="false"]')
      .first();
    await expect(expandableUnit).toBeVisible();
    await expandableUnit.click();
    await page
      .getByTestId("live-sessions-player-action-trigger")
      .first()
      .click();

    const menu = page.locator("#live-sessions-player-actions-menu:visible");
    await expect(menu).toHaveCount(1);
    await expect(menu.getByRole("menuitem").first()).toBeVisible();
    await expect(
      page.locator("#live-sessions-player-actions-menu")
    ).toHaveCount(1);
  });
});
