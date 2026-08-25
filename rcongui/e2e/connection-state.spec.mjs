import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.describe("connection state contract", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("distinguishes a CRCON outage from a game-server outage", async ({
    page,
  }) => {
    await openDemoPage(page, "/", {
      query: { demo_connection: "crcon_offline" },
    });

    await expect(
      page.getByText("CRCON · Offline", { exact: true })
    ).toBeVisible();
    await expect(
      page.getByTestId("gameserver-connection-status")
    ).toHaveAttribute("data-connection-state", "unknown");
  });

  test("shows CRCON online while the game server is offline", async ({
    page,
  }) => {
    await openDemoPage(page, "/", {
      query: { demo_connection: "gameserver_offline" },
    });

    await expect(
      page.getByText("CRCON · Online", { exact: true })
    ).toBeVisible();
    await expect(page.getByText("Offline", { exact: true })).toBeVisible();
  });

  test("marks cached game-server data as stale after a failed refresh", async ({
    page,
  }) => {
    await openDemoPage(page, "/", {
      query: { demo_connection: "gameserver_stale" },
    });

    await expect(
      page.getByTestId("gameserver-connection-status")
    ).toHaveAttribute("data-connection-state", "stale");
    await expect(
      page.getByText("Daten veraltet", { exact: true }).first()
    ).toBeVisible();
    await expect(
      page.getByText("Letzte Daten:", { exact: false })
    ).toBeVisible();
  });

  test("marks mixed live and cached sources as partial and freezes stale time", async ({
    page,
  }) => {
    await openDemoPage(page, "/", {
      query: { demo_connection: "game_state_stale" },
    });

    const status = page.getByTestId("global-match-status");
    await expect(status).toHaveAttribute("data-connection-state", "partial");
    await expect(status.getByText("98/100", { exact: true })).toBeVisible();
    await expect(
      status.getByText("Foy · Warfare · Nacht · Daten veraltet", {
        exact: true,
      })
    ).toBeVisible();

    const staleTime = status.getByText("00:57:07 · Daten veraltet", {
      exact: true,
    });
    await expect(staleTime).toBeVisible();
    await page.waitForTimeout(1_200);
    await expect(staleTime).toHaveText("00:57:07 · Daten veraltet");
    await expect(page).toHaveTitle(/Teilweise verfügbar/);
  });

  test("does not replace missing live data with believable example values", async ({
    page,
  }) => {
    const main = await openDemoPage(page, "/", {
      query: { demo_connection: "crcon_offline" },
    });
    const overview = main.getByTestId("battle-overview");

    await expect(
      overview.getByRole("heading", { name: "Unbekannter Server", exact: true })
    ).toBeVisible();
    await expect(
      overview.getByText("Unbekannte Karte", { exact: true }).first()
    ).toBeVisible();
    await expect(overview.getByText("Foy", { exact: true })).toHaveCount(0);
    await expect(overview.getByText("warfare", { exact: true })).toHaveCount(0);
    await expect(
      overview.getByText("[GER] Frontline Network | #2", { exact: true })
    ).toHaveCount(0);
  });
});
