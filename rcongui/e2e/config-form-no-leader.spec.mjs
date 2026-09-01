import { expect, test } from "@playwright/test";
import {
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";
import {
  noLeaderConfig,
  noLeaderFormContract,
  noLeaderSchema,
  noLeaderSectionIds,
} from "./fixtures/no-leader-config.mjs";

const path = "/settings/automods/no-leader";

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

async function openSection(shell, label, sectionId) {
  const navigation = shell.getByRole("navigation", {
    name: "Konfigurationsbereiche",
  });
  const button = navigation.getByRole("button", {
    name: new RegExp(`^${escapeRegExp(label)}`),
  });
  await button.click();
  await expect(button).toHaveAttribute("aria-current", "step");
  await expect(
    shell
      .getByTestId("config-guided-form")
      .locator(`[data-section="${sectionId}"]`)
  ).toBeVisible();
}

test("the No-Leader fixture represents the complete production configuration", () => {
  const fixtureFields = Object.keys(noLeaderConfig).sort();
  const schemaFields = Object.keys(noLeaderSchema.properties).sort();

  expect(fixtureFields).toEqual(schemaFields);
  expect(fixtureFields.length).toBeGreaterThanOrEqual(20);
  expect(noLeaderSchema.required).toEqual(
    expect.arrayContaining(
      fixtureFields.filter((field) => field !== "discord_webhook_url")
    )
  );

  for (const messageField of [
    "warning_message",
    "punish_message",
    "kick_message",
  ]) {
    expect(noLeaderConfig[messageField]).toContain("{squad_name}");
  }
});

for (const [viewportName, viewport] of [
  ["mobile", VIEWPORTS.mobile],
  ["desktop", VIEWPORTS.desktop],
]) {
  test(`renders the complete German form at ${viewport.width}px (${viewportName})`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    const main = await openDemoPage(page, path);
    const shell = main.getByTestId("config-page-shell");

    await expect(
      shell.getByRole("heading", {
        name: noLeaderFormContract.de.title,
        exact: true,
      })
    ).toBeVisible();
    await expect(
      shell.getByRole("group", { name: noLeaderFormContract.de.mode })
    ).toBeVisible();
    await expect(shell.getByRole("complementary").first()).toBeVisible();

    for (const [index, sectionId] of noLeaderSectionIds.entries()) {
      await openSection(
        shell,
        noLeaderFormContract.de.sections[index],
        sectionId
      );
      await expect(
        shell
          .getByRole("heading", {
            name: noLeaderFormContract.de.sections[index],
            exact: true,
          })
          .last()
      ).toBeVisible();
    }

    await expect(shell.getByTestId("config-mode-toggle")).toHaveCount(0);
    await expect(shell.getByTestId("config-json-editor")).toHaveCount(0);
    await expectNoHorizontalPageOverflow(page);
  });
}

test("uses natural English operator copy without exposing schema or JSON controls", async ({
  page,
}) => {
  const main = await openDemoPage(page, path, { language: "en" });
  const shell = main.getByTestId("config-page-shell");

  await expect(
    shell.getByRole("heading", {
      name: noLeaderFormContract.en.title,
      exact: true,
    })
  ).toBeVisible();

  const navigation = shell.getByRole("navigation", {
    name: "Configuration sections",
  });
  for (const section of noLeaderFormContract.en.sections) {
    await expect(
      navigation.getByRole("button", {
        name: new RegExp(`^${escapeRegExp(section)}`),
      })
    ).toBeVisible();
  }

  for (const implementationName of [
    "number_of_warnings",
    "kick_after_max_punish",
    "dont_do_anything_below_this_number_of_players",
  ]) {
    await expect(
      shell.getByText(implementationName, { exact: true })
    ).toHaveCount(0);
  }
  await expect(shell.getByTestId("config-json-editor")).toHaveCount(0);
});

test("keeps a numeric draft while navigating between sections", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("config-page-shell");

  await openSection(shell, "Erkennung", "detection");
  const input = shell.getByRole("spinbutton", {
    name: "Unsichtbare Prüfungen",
  });
  await input.fill("12");
  await expect(input).toHaveValue("12");
  const dirtyIndicator = shell.getByTestId("config-dirty-indicator");
  await expect(dirtyIndicator).toHaveText(noLeaderFormContract.de.dirty);
  await expect(shell.getByTestId("config-save-button")).toBeEnabled();

  await openSection(shell, "Ausnahmen", "exemptions");
  await openSection(shell, "Erkennung", "detection");
  await expect(
    shell.getByRole("spinbutton", { name: "Unsichtbare Prüfungen" })
  ).toHaveValue("12");
});

test("localizes message placeholders and updates the warning preview", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("config-page-shell");

  await openSection(shell, "Maßnahmen", "actions");
  const warningMessage = shell.getByRole("textbox", { name: "Warnnachricht" });
  await expect(warningMessage).toHaveValue(/\{Spielername\}/);
  await expect(warningMessage).toHaveValue(/\{Truppname\}/);
  await expect(warningMessage).not.toHaveValue(/\{player_name\}/);

  await shell.getByRole("button", { name: "Anzahl Warnungen +" }).click();
  await expect(shell).toContainText("Warnung 1 von 3");
  await expect(shell.getByRole("complementary").first()).toContainText(
    "3× · alle 60 Sekunden"
  );
});

test("makes unsaved changes explicit and lets the operator discard the draft", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("config-page-shell");
  const save = shell.getByTestId("config-save-button");
  const mode = shell.getByRole("group", { name: noLeaderFormContract.de.mode });
  const selectedMode = mode.locator('button[aria-pressed="true"]');
  const originalMode = (await selectedMode.textContent()).trim();
  const nextMode = originalMode === "Aktiv" ? "Beobachten" : "Aktiv";

  await expect(save).toBeDisabled();
  await mode.getByRole("button", { name: nextMode, exact: true }).click();
  await expect(shell.getByTestId("config-dirty-indicator")).toHaveText(
    noLeaderFormContract.de.dirty
  );
  await expect(save).toBeEnabled();

  await shell.getByTestId("config-reset-button").click();
  await expect(shell.getByTestId("config-dirty-indicator")).toHaveCount(0);
  await expect(save).toBeDisabled();
  await expect(
    mode.getByRole("button", { name: originalMode, exact: true })
  ).toHaveAttribute("aria-pressed", "true");
});

for (const [game, gameLabel] of [
  ["hll", "HLL"],
  ["hll_vietnam", "HLL: Vietnam"],
]) {
  test(`uses the shared squad-leader wording for ${gameLabel}`, async ({
    page,
  }) => {
    const main = await openDemoPage(page, path, {
      query: { demo_game: game },
    });

    await expect(main.getByTestId("config-page-shell")).toContainText(
      noLeaderFormContract.de.title
    );
    await expect(page.getByTestId("global-match-status").first()).toContainText(
      gameLabel
    );
    await expect(main.getByText(/Unit Leader|Einheitsführer/i)).toHaveCount(0);
  });
}
