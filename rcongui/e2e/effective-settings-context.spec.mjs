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

    await expect(main.getByTestId("admin-action-context")).toContainText(
      "Frontline #2"
    );
    await expect(main.getByTestId("admin-action-context")).toContainText("HLL");

    const vip = main.getByTestId("setting-effect-vip_slots_num");
    await expect(vip).toContainText("Zuletzt gelesener Serverwert");
    await expect(vip).toContainText("2 Plätze");
    await expect(vip).toContainText("FLN-Empfehlung");
    await expect(vip).toContainText("Im RCON-Protokoll: HLL und HLL Vietnam");
    await expect(main).toContainText(
      "Das aktuelle Spielprotokoll bestätigt den tatsächlich wirksamen Wert nicht zuverlässig"
    );
    await expect(vip).toContainText("Real VIP");
  });

  test("uses the same compatibility context for an HLL Vietnam installation", async ({
    page,
  }) => {
    const main = await openDemoPage(page, "/settings/general", {
      query: { demo_game: "hll_vietnam" },
    });

    await expect(main.getByTestId("admin-action-context")).toContainText(
      "HLL: Vietnam"
    );
    await expect(
      main.getByTestId("setting-effect-autobalance_threshold")
    ).toContainText("Im RCON-Protokoll: HLL und HLL Vietnam");
  });

  test("explains missing change permissions instead of enabling save", async ({
    page,
  }) => {
    const main = await openDemoPage(page, "/settings/general", {
      query: { demo_role: "viewer" },
    });

    const save = main.getByRole("button", { name: "Speichern" }).first();
    await expect(save).toBeDisabled();
    await save.hover({ force: true });
    await expect(
      page.getByText(
        "Dir fehlt die Berechtigung zum Ändern dieser Einstellung."
      )
    ).toBeVisible();
  });

  test("marks unsent drafts and can restore the recommendation", async ({
    page,
  }) => {
    const main = await openDemoPage(page, "/settings/general");
    const vipCard = main
      .getByRole("group")
      .filter({ has: page.getByText("VIP-Plätze", { exact: true }) });
    const input = vipCard.getByRole("spinbutton");

    await input.fill("5");
    await input.blur();
    await expect(vipCard).toContainText(
      "Der Wert im Formular wurde noch nicht an den Gameserver gesendet."
    );

    await vipCard.getByRole("button", { name: "Empfehlung einsetzen" }).click();
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
    await expect(
      main.getByTestId("setting-effect-vip_slots_num")
    ).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
  });
});
