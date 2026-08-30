import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.describe("game and server context", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("normalizes the HLL Vietnam API identifier", async ({ page }) => {
    await openDemoPage(page, "/", { query: { demo_game: "hll_vietnam" } });

    await expect(page.getByTestId("server-rail-switcher")).toHaveAccessibleName(
      /HLL: Vietnam/
    );
  });

  test("distinguishes HLL and HLL Vietnam in a multi-server installation", async ({
    page,
  }) => {
    await openDemoPage(page, "/", {
      query: {
        demo_game: "hll",
        demo_multiserver: 1,
        demo_other_game: "hll_vietnam",
      },
    });

    await page.getByTestId("server-rail-switcher").click();
    const menu = page.getByRole("menu", { name: "Server wechseln" });
    await expect(
      menu.getByRole("menuitem", { name: /Frontline #2.*HLL/ })
    ).toBeVisible();
    await expect(
      menu.getByRole("menuitem", { name: /Vietnam #3.*HLLV/ })
    ).toBeVisible();
  });

  test("does not invent a game label for an unknown identifier", async ({
    page,
  }) => {
    await openDemoPage(page, "/", { query: { demo_game: "future_game" } });

    await expect(page.getByText("HLL", { exact: true })).toHaveCount(0);
    await expect(page.getByText("HLL: Vietnam", { exact: true })).toHaveCount(
      0
    );
  });
});
