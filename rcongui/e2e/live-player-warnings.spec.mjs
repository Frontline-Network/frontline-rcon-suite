import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.use({ viewport: VIEWPORTS.desktop });

test("campaign recipients have no warning badge or warning count; moderation remains visible", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live", {
    query: { demo_warning_sources: 1 },
  });
  const panel = page.getByTestId("live-players-panel");
  await panel
    .getByRole("button", { name: "Tabelle anpassen", exact: true })
    .click();
  const settings = page.getByRole("dialog", { name: "Live-Ansicht anpassen" });
  await settings
    .getByRole("checkbox", { name: "Warnungen", exact: true })
    .check();
  await settings
    .getByRole("button", { name: "Speichern", exact: true })
    .click();
  await expect(settings).toHaveCount(0);
  for (const [name, warned] of [
    ["FLN_Raven", false], // 100 recent campaign messages
    ["FLN_Wolf", false], // VIP lifecycle message
    ["FLN_Valkyrie", true], // manual warning
    ["FLN_Hawkeye", true], // campaign + automod warning
    ["FLN_Falcon", true], // campaign + punishment
    ["FLN_Bravo", false], // campaign + expired manual warning
  ]) {
    const row = panel.locator('tr[data-player-row="true"]').filter({
      has: page.getByRole("button", {
        name: `Details zu ${name} anzeigen`,
        exact: true,
      }),
    });
    await expect(row).toHaveCount(1);
    await expect(
      row.getByRole("img", { name: "Verwarnt", exact: true })
    ).toHaveCount(warned ? 1 : 0);
    // The status badge and the optional legacy warning column use one rule.
    await expect(row.getByTestId("WarningIcon")).toHaveCount(warned ? 2 : 0);
    await row
      .getByRole("button", { name: `Details zu ${name} anzeigen`, exact: true })
      .click();
    const warningFact = page
      .getByTestId("live-player-detail-panel")
      .locator(".player-detail-status")
      .filter({ hasText: "Warnungen" });
    await expect(warningFact.locator("strong")).toHaveText(
      warned ? "1" : "Keine"
    );
    await panel
      .getByRole("button", {
        name: `Details zu ${name} schließen`,
        exact: true,
      })
      .click();
  }

  // Information is only excluded from warning indicators, never from history.
  // The dedicated profile fetch must agree with the compact live roster;
  // otherwise its late response can silently replace the message history.
  const profileActionCount = await page.evaluate(async () => {
    const response = await fetch(
      "/api/get_player_profile?player_id=76561198000000001"
    );
    const data = await response.json();
    return data.result.received_actions.filter(
      (action) => action.by === "Campaign: Mic-Pflicht DE"
    ).length;
  });
  expect(profileActionCount).toBe(100);
  await panel.getByRole("button", { name: "FLN_Raven", exact: true }).click();
  await page.getByRole("tab", { name: "Nachrichten", exact: true }).click();
  await expect(
    page
      .getByRole("tabpanel")
      .getByText("Campaign: Mic-Pflicht DE", { exact: false })
  ).toHaveCount(100);
});
