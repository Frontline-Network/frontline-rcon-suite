import { expect, test } from "@playwright/test";
import {
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

async function openDisbandDialog(page, options = {}) {
  await openDemoPage(page, "/views/team", options);
  await page.getByRole("button", { name: "Trupp auflösen" }).click();
  const dialog = page.getByRole("dialog", { name: "Trupps sicher auflösen" });
  await expect(dialog).toBeVisible();
  return dialog;
}

async function selectSquadAndReview(dialog, squadName = "able") {
  await dialog.getByText(new RegExp(`^${squadName} \\(`, "i")).click();
  await dialog
    .getByRole("textbox", { name: "Grund" })
    .fill("Test: sichere Adminaktion");
  await dialog.getByRole("button", { name: "Auswirkung prüfen" }).click();
}

test.describe("safe squad-disband action", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("shows server, game, connection and target context before execution", async ({
    page,
  }) => {
    const dialog = await openDisbandDialog(page);

    const context = dialog.getByTestId("admin-action-context");
    await expect(context).toContainText("Frontline #2");
    await expect(context).toContainText("Server 2");
    await expect(context).toContainText("HLL");
    await expect(context).toContainText("CRCON · Online");
    await expect(context).toContainText("Gameserver · Online");

    await selectSquadAndReview(dialog);
    await expect(dialog).toContainText("Alliierte · able");
    await expect(dialog).toContainText("Test: sichere Adminaktion");
    await expect(
      dialog.getByRole("button", {
        name: "Ausgewählte Trupps jetzt auflösen (1)",
      })
    ).toBeVisible();
  });

  test("uses the same safety context for HLL Vietnam", async ({ page }) => {
    const dialog = await openDisbandDialog(page, {
      query: { demo_game: "hll_vietnam" },
    });

    await expect(dialog.getByTestId("admin-action-context")).toContainText(
      "HLL: Vietnam"
    );
  });

  test("requires the review step and keeps a per-target result with an audit link", async ({
    page,
  }) => {
    const dialog = await openDisbandDialog(page);

    await expect(
      dialog.getByRole("button", { name: /jetzt auflösen/ })
    ).toHaveCount(0);
    await selectSquadAndReview(dialog);
    await dialog
      .getByRole("button", {
        name: "Ausgewählte Trupps jetzt auflösen (1)",
      })
      .click();

    await expect(dialog).toContainText("1 erfolgreich · 0 fehlgeschlagen");
    await expect(dialog).toContainText(
      "Trupp wurde aufgelöst und protokolliert."
    );
    await expect(
      dialog.getByRole("link", { name: "Audit-Protokoll öffnen" })
    ).toHaveAttribute("href", /commands=disband_squad_by_name/);
  });

  test("retries only a failed target", async ({ page }) => {
    const dialog = await openDisbandDialog(page, {
      query: { demo_disband_failure: "able" },
    });
    await selectSquadAndReview(dialog);
    await dialog
      .getByRole("button", {
        name: "Ausgewählte Trupps jetzt auflösen (1)",
      })
      .click();

    await expect(dialog).toContainText("0 erfolgreich · 1 fehlgeschlagen");
    await dialog
      .getByRole("button", {
        name: "Nur fehlgeschlagene erneut ausführen (1)",
      })
      .click();
    await expect(dialog).toContainText("1 erfolgreich · 0 fehlgeschlagen");
  });

  test("blocks execution when game-server data is offline", async ({
    page,
  }) => {
    const dialog = await openDisbandDialog(page, {
      query: { demo_connection: "gameserver_offline" },
    });
    await selectSquadAndReview(dialog);

    await expect(dialog).toContainText("Gameserver · Offline");
    await expect(dialog).toContainText(
      "Die Aktion ist gesperrt, bis CRCON und Gameserver wieder aktuelle Online-Daten liefern."
    );
    await expect(
      dialog.getByRole("button", {
        name: "Ausgewählte Trupps jetzt auflösen (1)",
      })
    ).toBeDisabled();
  });
});

test.describe("safe squad-disband action on mobile", () => {
  test.use({ viewport: VIEWPORTS.mobile });

  test("keeps the two-step flow usable at 390 px", async ({ page }) => {
    const dialog = await openDisbandDialog(page);
    await expectNoHorizontalPageOverflow(page);
    await selectSquadAndReview(dialog);
    await expect(
      dialog.getByRole("button", {
        name: "Ausgewählte Trupps jetzt auflösen (1)",
      })
    ).toBeVisible();
  });
});
