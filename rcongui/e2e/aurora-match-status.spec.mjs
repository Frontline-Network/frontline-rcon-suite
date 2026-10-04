import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  expectNoHorizontalPageOverflow,
  VIEWPORTS,
} from "./helpers.mjs";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem(
      "crcon.demo.appearance.admin",
      JSON.stringify({ preset: "wardogs", mode: "dark" })
    );
  });
});

const field = (status, name) => status.locator(`[data-status-field="${name}"]`);

for (const [name, viewport] of Object.entries({
  desktop: VIEWPORTS.desktop,
  laptop: { width: 1280, height: 900 },
  compactDesktop: { width: 1200, height: 900 },
  desktopBreakpoint: { width: 900, height: 900 },
  tablet: VIEWPORTS.tablet,
  mobile: VIEWPORTS.mobile,
  narrow: { width: 320, height: 740 },
})) {
  test(`shows all match details without overlap on ${name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize(viewport);
    await openDemoPage(page, "/views/live");

    const toolbar = page.getByTestId("wardogs-toolbar");
    const status = toolbar.getByTestId("global-match-status");
    await expect(status).toBeVisible();
    await expect(status).toHaveAttribute("data-connection-state", "online");
    await expect(field(status, "players")).toContainText("98/100");
    await expect(field(status, "map")).toContainText("Foy · Warfare · Nacht");
    await expect(field(status, "time")).toContainText(/00:5[0-7]:\d{2}/);
    await expect(status.getByText("Spieler", { exact: true })).toBeVisible();
    await expect(status.getByText("Karte", { exact: true })).toBeVisible();
    await expect(status.getByText("Restzeit", { exact: true })).toBeVisible();

    const bounds = await toolbar.boundingBox();
    const pageContext = await page
      .locator(".wardogs-page-context")
      .boundingBox();
    expect(pageContext.y).toBeGreaterThanOrEqual(bounds.y + bounds.height);
    let previousRight = 0;
    for (const name of ["players", "map", "time"]) {
      const box = await field(status, name).boundingBox();
      expect(box.x).toBeGreaterThanOrEqual(previousRight - 1);
      expect(box.x + box.width).toBeLessThanOrEqual(bounds.x + bounds.width);
      expect(box.y + box.height).toBeLessThanOrEqual(bounds.y + bounds.height);
      previousRight = box.x + box.width;
    }
    // Catch text clipped inside a field, not only document-level overflow.
    for (const name of ["players", "time"]) {
      const clipped = await field(status, name)
        .locator(".MuiTypography-body2")
        .evaluate((element) => element.scrollWidth > element.clientWidth + 1);
      expect(clipped).toBe(false);
    }
    await expectNoHorizontalPageOverflow(page);
    await page.screenshot({ path: testInfo.outputPath("aurora-status.png") });
  });
}

test("keeps match details on other pages and updates the live countdown", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.desktop);
  await openDemoPage(page, "/settings/general", {
    language: "en",
    query: { demo_game: "hll_vietnam" },
  });
  const status = page
    .getByTestId("wardogs-toolbar")
    .getByTestId("global-match-status");
  await expect(status.getByText("Players", { exact: true })).toBeVisible();
  await expect(status.getByText("Map", { exact: true })).toBeVisible();
  await expect(status.getByText("Remaining", { exact: true })).toBeVisible();
  await expect(field(status, "map")).toContainText("Cam Ranh Port");
  const time = field(status, "time").locator(".MuiTypography-body2");
  await expect(time).toHaveText(/\d{2}:\d{2}:\d{2}/);
  const initialTime = await time.textContent();
  await expect(time).not.toHaveText(initialTime);
});

test("marks cached values and freezes stale time", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/", {
    query: { demo_connection: "game_state_stale" },
  });
  const status = page
    .getByTestId("wardogs-toolbar")
    .getByTestId("global-match-status");
  await expect(status).toHaveAttribute("data-connection-state", "partial");
  await expect(field(status, "players")).toContainText("98/100");
  await expect(field(status, "map")).toContainText("Foy · Warfare · Nacht");
  await expect(
    field(status, "map").getByRole("img", { name: "Daten veraltet" })
  ).toBeVisible();
  await expect(
    field(status, "time").getByRole("img", { name: "Daten veraltet" })
  ).toBeVisible();
  const time = field(status, "time").locator(".MuiTypography-body2");
  await expect(time).toHaveText("00:57:07");
  await page.waitForTimeout(1200);
  await expect(time).toHaveText("00:57:07");
});

test("does not invent live values while the game server is offline", async ({
  page,
}) => {
  await openDemoPage(page, "/", {
    query: { demo_connection: "gameserver_offline" },
  });
  const status = page
    .getByTestId("wardogs-toolbar")
    .getByTestId("global-match-status");
  await expect(field(status, "players")).toContainText("Unbekannt");
  await expect(field(status, "time")).toContainText("Unbekannt");
  await expect(status).not.toContainText("98/100");
  await expect(status).not.toContainText("Foy");
  await expect(status).not.toContainText("00:57:07");
});
