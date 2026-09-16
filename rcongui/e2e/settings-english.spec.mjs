import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

test.use({ viewport: VIEWPORTS.desktop });

test("English autobalancer includes proposal details, dialogs and reactive language changes", async ({
  page,
}) => {
  const errors = collectRuntimeErrors(page);
  await openDemoPage(page, "/settings/others/autobalancer", { language: "en" });
  await expect(
    page.getByText(
      "Live state, proposal reviews and pilot approval for moderators"
    )
  ).toBeVisible();
  await expect(page.getByText("Shadow mode", { exact: true })).toBeVisible();
  await expect(
    page.getByText("No messages and no automatic player switches", {
      exact: true,
    })
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Review next proposal", exact: true })
    .click();
  await expect(
    page.getByText("Protected role?", { exact: true })
  ).toBeVisible();
  await expect(
    page.getByText("How much is the squad affected?", { exact: true })
  ).toBeVisible();
  await page.getByRole("button", { name: "Unacceptable", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Why is the candidate unacceptable?"
  );
  await expect(page.getByRole("dialog")).toContainText("Main reason");
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.getByRole("button", { name: "Language", exact: true }).click();
  await page.getByRole("menuitem", { name: "Deutsch", exact: true }).click();
  await expect(
    page.getByText("Geschützte Rolle?", { exact: true })
  ).toBeVisible();
  await page.getByRole("button", { name: "Sprache", exact: true }).click();
  await page.getByRole("menuitem", { name: "English", exact: true }).click();
  await expect(
    page.getByText("Protected role?", { exact: true })
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("English autobalancer history and calibration remain localized", async ({
  page,
}) => {
  await openDemoPage(page, "/settings/others/autobalancer", { language: "en" });
  await page.getByRole("tab", { name: "History", exact: true }).click();
  await page.getByRole("button", { name: /Browse past rounds/ }).click();
  await expect(
    page.getByRole("button", { name: "Search", exact: true })
  ).toBeVisible();
  await expect(
    page.getByRole("columnheader", { name: "Team history", exact: true })
  ).toBeVisible();
  await page.getByRole("tab", { name: "Pilot approval", exact: true }).click();
  await expect(
    page.getByText("Historical balance analysis", { exact: true })
  ).toBeVisible();
  await expect(
    page.getByText("Exact data coverage", { exact: true })
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Analyse", exact: true })
  ).toBeVisible();
  await expect(
    page.getByText("Historical balance analysis", { exact: true })
  ).toBeVisible();
  await expect(page.locator("#main-content")).not.toContainText(
    "Historische Balance-Auswertung"
  );
  await expect(page.locator("#main-content")).not.toContainText(
    "Bewertete Vorschläge"
  );
  await expectNoHorizontalPageOverflow(page);
});

test("English camera settings include controls, dirty state and explanatory text", async ({
  page,
}) => {
  await openDemoPage(page, "/settings/admin-cam-notifications", {
    language: "en",
  });
  await expect(
    page.getByText("No unsaved changes", { exact: true })
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Inactive", exact: true })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Active", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("button", { name: "Save changes", exact: true })
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Behavior and guidance", exact: true })
    .click();
  await expect(
    page.getByText(
      "These settings only affect entering the admin camera. Other moderation messages are unchanged."
    )
  ).toBeVisible();
  await expect(page.locator("#main-content")).not.toContainText(
    "Werte zurücksetzen"
  );
  await expect(page.locator("#main-content")).not.toContainText(
    "Keine ungespeicherten Änderungen"
  );
});

for (const viewportName of ["desktop", "mobile"]) {
  test(`English Discord and leadership settings on ${viewportName}`, async ({
    page,
  }) => {
    await page.setViewportSize(VIEWPORTS[viewportName]);
    const errors = collectRuntimeErrors(page);
    await openDemoPage(page, "/apps/discord-report-bot", {
      language: "en",
      query: { demo_discord: "connected", demo_game: "hll_vietnam" },
    });
    const navigation = page.getByRole("navigation", {
      name: "Discord Report Bot setup progress",
    });
    const steps = [
      "Connect Discord",
      "Detect server",
      "Channel & roles",
      "Actions",
      "Optional AI",
      "Test",
      "Activate",
    ];
    for (const [index, label] of steps.entries()) {
      if (viewportName === "mobile") {
        await navigation
          .getByRole("combobox", { name: "Current setup step" })
          .click();
        await page
          .getByRole("option", { name: `${index + 1}. ${label}`, exact: true })
          .click();
      } else {
        await navigation
          .getByRole("button", { name: label, exact: true })
          .click();
      }
    }
    const leadership = page.getByRole("region", {
      name: "Leadership vote",
      exact: true,
    });
    await expect(leadership).toContainText("Minimum eligible voters");
    await expect(leadership).toContainText("No majority – admins needed");
    await expect(leadership).toContainText("Demo: no majority – no kick");
    // An allegation is player-owned content, not UI copy, and must be preserved.
    await expect(leadership).toContainText(
      "Squad gemeldet – Kommunikation prüfen"
    );
    await expect(leadership).not.toContainText(
      "Demo: Zustimmung nicht erreicht"
    );
    await expectNoHorizontalPageOverflow(page);
    expect(errors).toEqual([]);
  });
}
