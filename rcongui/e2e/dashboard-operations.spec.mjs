import { expect, test } from "@playwright/test";
import {
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
  test(`${viewportName} dashboard opens the right operational workspace`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await openDemoPage(page, "/", {
      query: { demo_game: "hll_vietnam" },
    });

    if (viewportName === "desktop") {
      const overview = page.getByTestId("operations-overview");
      await expect(overview).toBeVisible();
      await expect(page.getByText("Schichtlage")).toBeVisible();
      await expect(page.getByText("Offene Aufgaben")).toBeVisible();
      await expect(page.getByText("Live-Teamstatus")).toBeVisible();
      await expect(page.getByText("Aktuelle Runde")).toBeVisible();
      await expect(page.getByText("Letzte Ereignisse")).toBeVisible();
      await expect(
        overview.getByRole("link", { name: /Live-Ansicht öffnen/ })
      ).toHaveAttribute("href", "/views/live");
      await expect(
        overview.getByRole("link", { name: /^Teams$/ })
      ).toHaveAttribute("href", "/views/team");

      await expect(page.getByTestId("resource-telemetry-card")).toHaveCount(0);
      await expect(page.getByText("Ressourcen & Kapazität")).toHaveCount(0);
      await expect(page.getByText("Dienste", { exact: true })).toHaveCount(0);
    } else {
      await expect(page.getByRole("region", { name: "Betrieb" })).toBeVisible();
      await expect(
        page.getByRole("link", { name: /Teams & Trupps/ })
      ).toHaveAttribute("href", "/views/team");
      await expect(
        page.getByRole("link", { name: /Autobalancer/ })
      ).toHaveAttribute("href", "/views/autobalancer");
    }

    const visibleMatchStatus = page
      .getByTestId("global-match-status")
      .filter({ visible: true })
      .first();
    await expect(visibleMatchStatus).toContainText("HLL: Vietnam");
    await expectNoHorizontalPageOverflow(page);
  });
}

test.describe("desktop operational overview", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("uses current match, live team and activity data without technical widgets", async ({
    page,
  }) => {
    await openDemoPage(page, "/");
    const overview = page.getByTestId("operations-overview");

    await expect(
      overview.getByText("[GER] Frontline Network | #2")
    ).toBeVisible();
    await expect(overview.getByText("98/100")).toBeVisible();
    await expect(
      overview.getByText("Stärke-Index", { exact: true }).first()
    ).toBeVisible();
    await expect(overview.getByText("VIP online")).toBeVisible();
    await expect(overview.getByText("Letzte Ereignisse")).toBeVisible();
  });

  test("keeps the operational dashboard game-neutral in English", async ({
    page,
  }) => {
    await openDemoPage(page, "/", {
      language: "en",
      query: { demo_game: "hll" },
    });

    await expect(
      page.getByTestId("global-server-switcher").filter({ visible: true }).first()
    ).toContainText("HLL");
    await expect(
      page.getByText("Operational situation of the selected game server")
    ).toBeVisible();
    await expect(page.getByText("Live team status")).toBeVisible();
    await expect(page.getByText("Resources & capacity")).toHaveCount(0);
    await expect(page.getByText("HLL: Vietnam", { exact: true })).toHaveCount(0);
  });
});
