import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.describe("live player density and details", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("places team and squad before the player name", async ({ page }) => {
    await openDemoPage(page, "/views/live");

    const headers = await page
      .getByTestId("live-players-panel")
      .locator("thead th")
      .allTextContents();
    const normalizedHeaders = headers.map((header) => header.trim());
    const teamIndex = normalizedHeaders.indexOf("Team");
    const squadIndex = normalizedHeaders.indexOf("Trupp");
    const playerIndex = normalizedHeaders.indexOf("Name");

    expect(teamIndex).toBeGreaterThanOrEqual(0);
    expect(squadIndex).toBeGreaterThan(teamIndex);
    expect(playerIndex).toBeGreaterThan(squadIndex);
    expect(normalizedHeaders).not.toContain("Team / Trupp / Rolle");
  });

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
    const detailPanel = panel.getByTestId("live-player-detail-panel");
    await expect(detailPanel).toHaveCount(1);

    const expandedRowBox = await panel
      .locator('tr[data-player-row="true"][data-expanded="true"]')
      .first()
      .boundingBox();
    const detailBox = await detailPanel.boundingBox();
    expect(
      Math.abs((expandedRowBox?.x ?? 0) - (detailBox?.x ?? 0))
    ).toBeLessThan(4);
    expect(detailBox?.width).toBeLessThanOrEqual(
      (await panel.boundingBox())?.width ?? Number.POSITIVE_INFINITY
    );

    const statTops = await detailPanel
      .locator(".player-detail-stat")
      .evaluateAll((elements) =>
        elements.map((element) =>
          Math.round(element.getBoundingClientRect().top)
        )
      );
    expect(new Set(statTops).size).toBe(1);

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

  test("routes every row trigger through one shared action menu", async ({
    page,
  }) => {
    await openDemoPage(page, "/views/live");

    const panel = page.getByTestId("live-players-panel");
    const triggers = panel.getByTestId("live-player-row-actions-trigger");
    await expect.poll(() => triggers.count()).toBeGreaterThan(1);

    const firstPlayerName = await triggers
      .nth(0)
      .getAttribute("data-player-name");
    const secondPlayerName = await triggers
      .nth(1)
      .getAttribute("data-player-name");
    expect(firstPlayerName).toBeTruthy();
    expect(secondPlayerName).toBeTruthy();
    expect(secondPlayerName).not.toBe(firstPlayerName);

    await triggers.nth(0).click();
    const firstMenu = page.getByRole("menu");
    await expect(firstMenu).toBeVisible();
    await firstMenu.getByRole("menuitem", { name: "Nachricht senden" }).click();

    const firstDialog = page.getByRole("dialog", { name: "Nachricht senden" });
    await expect(firstDialog).toBeVisible();
    await expect(
      firstDialog.getByText(firstPlayerName, { exact: true })
    ).toBeVisible();
    await firstDialog.getByRole("button", { name: "Schließen" }).click();
    await expect(firstDialog).toHaveCount(0);

    await triggers.nth(1).click();
    const secondMenu = page.getByRole("menu");
    await secondMenu
      .getByRole("menuitem", { name: "Nachricht senden" })
      .click();

    const secondDialog = page.getByRole("dialog", { name: "Nachricht senden" });
    await expect(
      secondDialog.getByText(secondPlayerName, { exact: true })
    ).toBeVisible();
    await expect(
      secondDialog.getByText(firstPlayerName, { exact: true })
    ).toHaveCount(0);
  });

  test("keeps the expanded inspector usable at tablet width", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 768, height: 900 });
    await openDemoPage(page, "/views/live");

    const panel = page.getByTestId("live-players-panel");
    await panel
      .getByRole("button", { name: /Details zu .* (anzeigen|öffnen)/ })
      .first()
      .click();

    // Tablet width uses the mobile inspector sheet, which is rendered through
    // a portal outside the players panel. Its content contract stays identical.
    const detailPanel = page.getByTestId("live-player-detail-panel");
    await expect(detailPanel).toBeVisible();

    const overflow = await detailPanel.evaluate((element) => ({
      clientWidth: element.clientWidth,
      scrollWidth: element.scrollWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);

    const buttons = detailPanel.getByRole("button");
    const buttonCount = await buttons.count();
    for (let index = 0; index < buttonCount; index += 1) {
      const box = await buttons.nth(index).boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
      expect(box?.width).toBeGreaterThanOrEqual(44);
    }
  });

  test("keeps players in page flow and isolates log scrolling in split mode", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1920, height: 1000 });
    await openDemoPage(page, "/views/live");

    await page.getByRole("button", { name: "Geteilt" }).click();

    const playersPanel = page.getByTestId("live-players-panel");
    const logsPanel = page.getByTestId("live-logs-panel");
    const tableLayout = page.getByTestId("live-player-table-layout");
    const tableViewport = tableLayout.locator(":scope > :last-child");
    const eventStream = page.getByTestId("live-event-stream");

    await expect(playersPanel).toBeVisible();
    await expect(logsPanel).toBeVisible();

    const playerScroll = await tableViewport.evaluate((element) => ({
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
    }));
    const logScroll = await eventStream.evaluate((element) => ({
      clientHeight: element.clientHeight,
      overflowY: getComputedStyle(element).overflowY,
      overscrollBehaviorY: getComputedStyle(element).overscrollBehaviorY,
      scrollHeight: element.scrollHeight,
      tabIndex: element.tabIndex,
    }));
    expect(playerScroll.scrollHeight).toBeLessThanOrEqual(
      playerScroll.clientHeight + 1
    );
    expect(logScroll.overflowY).toBe("auto");
    expect(logScroll.overscrollBehaviorY).toBe("contain");
    expect(logScroll.tabIndex).toBe(0);

    await playersPanel.evaluate((element) => {
      // The fake server has only a few players. A tall panel reproduces the
      // natural document height of a populated 100-player server without
      // introducing another vertical scroll container.
      element.style.minHeight = "1800px";
    });

    const pageScroller = page.locator("main#main-content");
    const pageScroll = await pageScroller.evaluate((element) => ({
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
    }));
    expect(pageScroll.scrollHeight).toBeGreaterThan(pageScroll.clientHeight);

    const stickyTop = await logsPanel.evaluate((element) =>
      Number.parseFloat(getComputedStyle(element).top)
    );
    expect(
      await logsPanel.evaluate((element) => getComputedStyle(element).position)
    ).toBe("sticky");

    await pageScroller.evaluate((element) => {
      element.scrollTop = 700;
    });
    await expect
      .poll(() => pageScroller.evaluate((element) => element.scrollTop))
      .toBeGreaterThan(0);
    await expect
      .poll(() =>
        logsPanel.evaluate((element) => element.getBoundingClientRect().top)
      )
      .toBeCloseTo(stickyTop, 0);

    const pageScrollBeforeLog = await pageScroller.evaluate(
      (element) => element.scrollTop
    );
    await eventStream.evaluate((element) => {
      element.scrollTop = 240;
    });
    expect(
      await eventStream.evaluate((element) => element.scrollTop)
    ).toBeGreaterThan(0);
    expect(await pageScroller.evaluate((element) => element.scrollTop)).toBe(
      pageScrollBeforeLog
    );
  });
});
