import { expect, test } from "@playwright/test";
import { expectNoHorizontalPageOverflow, openDemoPage, VIEWPORTS } from "./helpers.mjs";

const orderedSections = ["dashboard-section-operations", "resource-telemetry-card", "dashboard-section-moderation", "dashboard-section-configuration", "dashboard-section-analysis", "dashboard-section-apps"];

for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
  test(`${viewportName} dashboard keeps operations before promotion`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await openDemoPage(page, "/", {
      query: { demo_game: "hll_vietnam" },
    });

    const positions = await page.evaluate((testIds) => {
      return testIds.map((testId) => {
        const element = document.querySelector(`[data-testid="${testId}"]`);
        return {
          testId,
          top: element ? element.getBoundingClientRect().top + window.scrollY : null,
        };
      });
    }, orderedSections);

    expect(positions.every(({ top }) => Number.isFinite(top))).toBe(true);
    for (let index = 1; index < positions.length; index += 1) {
      expect(positions[index].top, `${positions[index].testId} must follow ${positions[index - 1].testId}`).toBeGreaterThan(positions[index - 1].top);
    }

    await expect(page.getByTestId("global-match-status")).toContainText(
      "HLL: Vietnam"
    );
    await expect(page.getByText("Zentrale Übersicht des ausgewählten Gameservers")).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
  });
}

test.describe("dashboard resource states", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("shows current used and total capacity with provenance", async ({ page }) => {
    await openDemoPage(page, "/");
    const card = page.getByTestId("resource-telemetry-card");

    await expect(card.getByTestId("resource-status")).toHaveText("Normal");
    await expect(card.getByText(/0,72 \/ 4 Kerne verwendet/)).toBeVisible();
    await expect(card.getByText(/3,68 \/ 8 GiB verwendet/)).toBeVisible();
    await expect(card.getByText(/Quelle: Container \(cgroup v2\)/).first()).toBeVisible();
    await expect(card.getByText(/Warnung ab 80 %/)).toBeVisible();
    await expect(card.getByRole("progressbar", { name: "CPU" })).toHaveAttribute("aria-valuetext", "18 Prozent verwendet");
  });

  const resourceStates = [
    {
      mode: "warning",
      label: "Warnung",
      message: /RAM liegt bei 86 %/,
    },
    {
      mode: "stale",
      label: "Daten veraltet",
      message: /letzte erfolgreiche Messung bleibt sichtbar/,
    },
    {
      mode: "partial",
      label: "Teilweise verfügbar",
      message: /Teil der Ressourcenmessung ist nicht verfügbar/,
    },
    {
      mode: "unavailable",
      label: "Nicht verfügbar",
      message: /keine belastbaren Ressourcenwerte/,
    },
  ];

  for (const state of resourceStates) {
    test(`explains the ${state.mode} resource state`, async ({ page }) => {
      await openDemoPage(page, "/", {
        query: { demo_resources: state.mode },
      });
      const card = page.getByTestId("resource-telemetry-card");
      await expect(card.getByTestId("resource-status")).toHaveText(state.label);
      await expect(card.getByText(state.message)).toBeVisible();
    });
  }

  test("opens moderation incidents as the first log category", async ({ page }) => {
    await openDemoPage(page, "/");

    await expect(page.getByRole("tab", { name: /Admin-Meldungen/ })).toHaveAttribute("aria-selected", "true");
  });

  test("keeps the HLL dashboard and resource contract game-neutral in English", async ({ page }) => {
    await openDemoPage(page, "/", {
      language: "en",
      query: { demo_game: "hll" },
    });

    await expect(page.getByText("HLL", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Central overview of the selected game server")).toBeVisible();
    await expect(page.getByText("Resources & capacity")).toBeVisible();
    await expect(page.getByText("HLL: Vietnam", { exact: true })).toHaveCount(0);
  });
});
