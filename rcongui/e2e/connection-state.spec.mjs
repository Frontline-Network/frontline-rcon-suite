import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.describe("connection state contract", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("distinguishes a CRCON outage from a game-server outage", async ({ page }) => {
    await openDemoPage(page, "/", {
      query: { demo_connection: "crcon_offline" },
    });

    await expect(page.getByText("CRCON · Offline", { exact: true })).toBeVisible();
    await expect(page.getByText("Unbekannt", { exact: true })).toBeVisible();
  });

  test("shows CRCON online while the game server is offline", async ({ page }) => {
    await openDemoPage(page, "/", {
      query: { demo_connection: "gameserver_offline" },
    });

    await expect(page.getByText("CRCON · Online", { exact: true })).toBeVisible();
    await expect(page.getByText("Offline", { exact: true })).toBeVisible();
  });
});
