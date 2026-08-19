import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.describe("player-action permissions", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("does not expose protected game actions to a viewer", async ({ page }) => {
    await openDemoPage(page, "/views/team", { query: { demo_role: "viewer" } });

    await page.getByRole("button", { name: "Spieleraktionen" }).first().click();
    await expect(
      page.getByText("Dir fehlt die erforderliche Berechtigung für diese Aktionen.", { exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Spieler bestrafen" })).toHaveCount(0);
    await expect(page.getByRole("menuitem", { name: "Spieler kicken" })).toHaveCount(0);
  });

  test("keeps protected game actions available to a superuser", async ({ page }) => {
    await openDemoPage(page, "/views/team");

    await page.getByRole("button", { name: "Spieleraktionen" }).first().click();
    await expect(page.getByRole("menuitem", { name: "Spieler bestrafen" })).toBeVisible();
    await expect(page.getByRole("menuitem", { name: "Spieler kicken" })).toBeVisible();
  });
});
