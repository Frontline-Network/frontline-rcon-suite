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

    const actionTrigger = page.getByTestId(
      "live-sessions-player-action-trigger"
    );
    await expect(actionTrigger.first()).toBeVisible();
    await actionTrigger.first().click();

    const menu = page.locator("#live-sessions-player-actions-menu:visible");
    await expect(menu).toHaveCount(1);
    await expect(menu.getByRole("menuitem").first()).toBeVisible();
    await expect(
      page.locator("#live-sessions-player-actions-menu")
    ).toHaveCount(1);
  });

  test("opens one shared menu from a completed-game player row", async ({
    page,
  }) => {
    await openDemoPage(page, "/stats/games/fln-demo-1");

    const actionTrigger = page.getByTestId(
      "completed-game-player-action-trigger"
    );
    await expect.poll(() => actionTrigger.count()).toBeGreaterThan(1);
    await actionTrigger.first().click();

    const menu = page.locator("#completed-game-player-actions-menu:visible");
    await expect(menu).toHaveCount(1);
    await expect(menu.getByRole("menuitem").first()).toBeVisible();
    await expect(
      page.locator("#completed-game-player-actions-menu")
    ).toHaveCount(1);
  });

  test("the historical timeline does not mount per-event action menus", async ({
    page,
  }) => {
    await openDemoPage(page, "/records/game-logs");

    await expect(page.getByTestId("game-log-player-action-trigger")).toHaveCount(0);
    await expect(page.locator("#game-log-player-actions-menu")).toHaveCount(0);
  });

  test("reuses the historical-log menu inside a player profile", async ({
    page,
  }) => {
    await openDemoPage(page, "/records/players/76561198000000001/logs");

    await page.getByTestId("game-log-player-action-trigger").first().click();

    const menu = page.locator("#game-log-player-actions-menu:visible");
    await expect(menu).toHaveCount(1);
    await expect(menu.getByRole("menuitem").first()).toBeVisible();
    await expect(page.locator("#game-log-player-actions-menu")).toHaveCount(1);
  });
});

test.describe("shared player action menu on mobile", () => {
  test.use({ viewport: VIEWPORTS.mobile });

  test("reuses the live-session menu for mobile player cards", async ({
    page,
  }) => {
    await openDemoPage(page, "/stats/live-sessions");

    const actionTrigger = page.getByTestId(
      "live-sessions-player-action-trigger"
    );
    await expect(actionTrigger.first()).toBeVisible();
    await actionTrigger.first().click();

    const menu = page.locator("#live-sessions-player-actions-menu:visible");
    await expect(menu).toHaveCount(1);
    await expect(menu.getByRole("menuitem").first()).toBeVisible();
    await expect(
      page.locator("#live-sessions-player-actions-menu")
    ).toHaveCount(1);
  });

  test("reuses the completed-game menu for mobile player cards", async ({
    page,
  }) => {
    await openDemoPage(page, "/stats/games/fln-demo-1");

    const actionTrigger = page.getByTestId(
      "completed-game-player-action-trigger"
    );
    await expect.poll(() => actionTrigger.count()).toBeGreaterThan(1);
    await actionTrigger.first().click();

    const menu = page.locator("#completed-game-player-actions-menu:visible");
    await expect(menu).toHaveCount(1);
    await expect(menu.getByRole("menuitem").first()).toBeVisible();
    await expect(
      page.locator("#completed-game-player-actions-menu")
    ).toHaveCount(1);
  });

  test("keeps the historical timeline action-menu free on mobile", async ({
    page,
  }) => {
    await openDemoPage(page, "/records/game-logs");

    await expect(page.getByTestId("game-log-player-action-trigger")).toHaveCount(0);
    await expect(page.locator("#game-log-player-actions-menu")).toHaveCount(0);
  });
});
