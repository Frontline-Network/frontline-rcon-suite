import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

async function enableCommanderCards(page) {
  await page
    .getByRole("button", { name: "Live-Ansicht anpassen", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Live-Ansicht anpassen" });
  await dialog
    .getByRole("checkbox", { name: "Commander-Hinweise (beide Teams)" })
    .check();
  await dialog.getByRole("button", { name: "Speichern", exact: true }).click();
  await expect(dialog).toHaveCount(0);
}

test.describe("live status shortcuts", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("keeps the workspace controls without duplicating the global live status", async ({
    page,
  }) => {
    await openDemoPage(page, "/views/live");

    const commandBar = page.getByRole("region", { name: "Live-Einsatz" });

    await expect(commandBar).toBeVisible();
    await expect(
      commandBar.getByRole("heading", { name: "Live-Einsatz" })
    ).toBeVisible();
    await expect(
      commandBar.getByText("Aktuelle Karte", { exact: true })
    ).toHaveCount(0);
    await expect(commandBar.getByText("Restzeit", { exact: true })).toHaveCount(
      0
    );
    await expect(
      commandBar.getByRole("button", { name: "Geteilt" })
    ).toBeVisible();
  });

  test("toggles a commander warning off and restores every player", async ({
    page,
  }) => {
    await openDemoPage(page, "/views/live");

    const players = page.getByTestId("live-players-panel");
    await enableCommanderCards(page);
    const rows = players.getByRole("row");
    const initialRowCount = await rows.count();
    const commanderWarning = page
      .getByRole("button", { name: /Kein Commander/ })
      .first();

    await expect(commanderWarning).toBeVisible();
    await commanderWarning.click();
    await expect(commanderWarning).toHaveAttribute("aria-pressed", "true");
    await expect.poll(() => rows.count()).toBeLessThan(initialRowCount);

    await commanderWarning.click();
    await expect(commanderWarning).toHaveAttribute("aria-pressed", "false");
    await expect(rows).toHaveCount(initialRowCount);
  });

  test("the selected All shortcut clears a status-card filter", async ({
    page,
  }) => {
    await openDemoPage(page, "/views/live");

    const players = page.getByTestId("live-players-panel");
    await enableCommanderCards(page);
    const rows = players.getByRole("row");
    const initialRowCount = await rows.count();
    const commanderWarning = page
      .getByRole("button", { name: /Kein Commander/ })
      .first();
    const allPlayers = players.getByRole("button", { name: /^Alle \d+$/ });

    await commanderWarning.click();
    await expect.poll(() => rows.count()).toBeLessThan(initialRowCount);

    await allPlayers.click();
    await expect(rows).toHaveCount(initialRowCount);
    await expect(commanderWarning).toHaveAttribute("aria-pressed", "false");
  });
});
