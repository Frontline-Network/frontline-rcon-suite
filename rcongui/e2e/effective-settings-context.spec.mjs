import { expect, test } from "@playwright/test";
import {
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

test.describe("effective server-settings context", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("shows server, game, source and protocol limitations", async ({
    page,
  }) => {
    const main = await openDemoPage(page, "/settings/general");
    const matrix = main.getByTestId("general-settings-operations-matrix");

    await expect(matrix).toContainText("Frontline #2 · Server 2");
    await expect(matrix).toContainText("CRCON · Online");
    await expect(matrix).toContainText("Gameserver · Online");
    await expect(matrix).toContainText("Werte nicht verifiziert");

    await matrix.getByRole("button", { name: "Zugang & Plätze" }).click();
    const vip = matrix.getByTestId("general-setting-vip_slots_num");
    await expect(vip).toContainText("2 Plätze");
    await expect(vip).toContainText("1–2 Plätze");
    await expect(vip).toContainText("Gespeichert");
  });

  test("uses the same compatibility context for an HLL Vietnam installation", async ({
    page,
  }) => {
    const main = await openDemoPage(page, "/settings/general", {
      query: { demo_game: "hll_vietnam" },
    });

    await expect(page.getByTestId("global-match-status").first()).toContainText(
      "HLL: Vietnam"
    );
    const matrix = main.getByTestId("general-settings-operations-matrix");
    await matrix.getByRole("button", { name: "Teamausgleich" }).click();
    await expect(
      matrix.getByTestId("general-setting-autobalance_threshold")
    ).toBeVisible();
  });

  test("explains missing change permissions instead of enabling save", async ({
    page,
  }) => {
    const main = await openDemoPage(page, "/settings/general", {
      query: { demo_role: "viewer" },
    });

    const matrix = main.getByTestId("general-settings-operations-matrix");
    const save = matrix.getByRole("button", {
      name: "Änderungen speichern",
    });
    await expect(save).toBeDisabled();
    await expect(matrix.getByRole("spinbutton").first()).toBeDisabled();
  });

  test("marks unsent drafts and can restore the recommendation", async ({
    page,
  }) => {
    const main = await openDemoPage(page, "/settings/general");
    const matrix = main.getByTestId("general-settings-operations-matrix");
    await matrix.getByRole("button", { name: "Zugang & Plätze" }).click();
    const vipCard = matrix.getByTestId("general-setting-vip_slots_num");
    const input = vipCard.getByRole("spinbutton");

    await input.fill("5");
    await input.blur();
    await expect(vipCard).toContainText("Geändert");

    await vipCard.getByRole("button", { name: "1–2 Plätze" }).click();
    await expect(input).toHaveValue("2");
  });

  test("does not present missing dashboard data as disabled settings", async ({
    page,
  }) => {
    const main = await openDemoPage(page, "/", {
      query: { demo_settings_error: "1" },
    });

    const heading = main.getByText("Servereinstellungen", { exact: true });
    const card = heading.locator(
      "xpath=ancestor::*[contains(@class, 'MuiCard-root')]"
    );
    await expect(card).toContainText(
      "Die Servereinstellungen sind derzeit nicht verfügbar"
    );
    await expect(card.getByText("Deaktiviert", { exact: true })).toHaveCount(0);
  });
});

test.describe("effective settings on mobile", () => {
  test.use({ viewport: VIEWPORTS.mobile });

  test("keeps the setting context usable at 390 px", async ({ page }) => {
    const main = await openDemoPage(page, "/settings/general");
    const matrix = main.getByTestId("general-settings-operations-matrix");
    await matrix.getByRole("combobox", { name: "Einstellung" }).click();
    await page.getByRole("option", { name: "Zugang & Plätze" }).click();
    await expect(
      matrix.getByTestId("general-setting-vip_slots_num")
    ).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
  });
});
