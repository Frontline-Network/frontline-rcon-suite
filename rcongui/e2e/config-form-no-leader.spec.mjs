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

    await expect(shell).toBeVisible();
    await expect(
      shell.getByRole("heading", {
        name: noLeaderFormContract.de.title,
        exact: true,
      })
    ).toBeVisible();

    for (const [index, sectionId] of noLeaderSectionIds.entries()) {
      const section = shell.getByTestId(`config-section-${sectionId}`);
      await expect(section).toBeAttached();
      await expect(section).toContainText(
        noLeaderFormContract.de.sections[index]
      );
    }

    for (const label of noLeaderFormContract.de.labels) {
      await expect(
        shell.getByText(label, { exact: true }).first()
      ).toBeAttached();
    }

    await expectNoHorizontalPageOverflow(page);
  });
}

test("uses natural English operator copy without exposing raw schema names", async ({
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

  for (const [index, sectionId] of noLeaderSectionIds.entries()) {
    await expect(
      shell.getByTestId(`config-section-${sectionId}`)
    ).toContainText(noLeaderFormContract.en.sections[index]);
  }

  for (const label of noLeaderFormContract.en.labels) {
    await expect(
      shell.getByText(label, { exact: true }).first()
    ).toBeAttached();
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
});

test("switches between the guided form and advanced JSON without losing the draft", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const modeToggle = main.getByTestId("config-mode-toggle");
  const form = main.getByTestId("config-guided-form");

  await expect(form).toBeVisible();
  await modeToggle
    .getByRole("button", { name: noLeaderFormContract.de.tabs[1] })
    .click();
  await expect(main.getByTestId("config-json-editor")).toBeVisible();
  await expect(main.getByTestId("config-json-editor")).toContainText(
    "number_of_warnings"
  );

  await modeToggle
    .getByRole("button", { name: noLeaderFormContract.de.tabs[0] })
    .click();
  await expect(form).toBeVisible();
  await main
    .getByRole("button", { name: "Warnen Warnungen konfigurieren" })
    .click();
  await expect(
    form.getByText("Warnungen vor der Bestrafung", { exact: true })
  ).toBeVisible();
});

test("shows localized message placeholders while keeping backend tokens in JSON", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("config-page-shell");

  await shell
    .getByRole("button", { name: "Warnen Warnungen konfigurieren" })
    .click();

  const warningMessage = shell
    .getByTestId("config-section-warnings")
    .locator("textarea")
    .first();
  await expect(warningMessage).toHaveValue(/\{Spielername\}/);
  await expect(warningMessage).toHaveValue(/\{Truppname\}/);
  await expect(warningMessage).not.toHaveValue(/\{player_name\}/);

  await shell
    .getByTestId("config-section-warnings")
    .getByText("Max. Warnungen", { exact: true })
    .click();
  await expect(warningMessage).toHaveValue(/\{Max\. Warnungen\}/);
  await expect(
    shell.getByText(/Unbekannte Platzhalter:.*max_warnings/)
  ).toHaveCount(0);

  await warningMessage.fill(
    "Hallo {Spielername} aus {Truppname}: {Max. Warnungen}"
  );
  await shell
    .getByTestId("config-mode-toggle")
    .getByRole("button", { name: noLeaderFormContract.de.tabs[1] })
    .click();
  await expect(shell.getByTestId("config-json-editor")).toContainText(
    "Hallo {player_name} aus {squad_name}: {max_warnings}"
  );

  await shell
    .getByTestId("config-mode-toggle")
    .getByRole("button", { name: noLeaderFormContract.de.tabs[0] })
    .click();
  await shell
    .getByRole("button", { name: "Warnen Warnungen konfigurieren" })
    .click();
  await expect(warningMessage).toHaveValue(
    "Hallo {Spielername} aus {Truppname}: {Max. Warnungen}"
  );
});

test("guided number fields keep the operator draft while replacing a value", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("config-page-shell");

  await shell
    .getByRole("navigation", { name: "Konfigurationsbereiche" })
    .getByRole("button", { name: /^Bestätigen/ })
    .click();

  const input = shell.getByRole("spinbutton", {
    name: "Unsichtbare Prüfungen",
  });
  await input.click();
  await input.press("ControlOrMeta+A");
  await input.press("Backspace");
  await expect(input).toHaveValue("");
  await input.pressSequentially("12");
  await page.waitForTimeout(400);
  await expect(input).toHaveValue("12");

  await shell
    .getByTestId("config-mode-toggle")
    .getByRole("button", { name: "JSON (erweitert)" })
    .click();
  await expect(shell.getByTestId("config-json-editor")).toContainText(
    '"number_of_notes": 12'
  );
});

test("updates the warning preview and action sequence from the stepper", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("config-page-shell");

  await shell
    .getByRole("button", { name: "Warnen Warnungen konfigurieren" })
    .click();
  await shell.getByRole("button", { name: "Anzahl Warnungen +" }).click();

  await expect(shell).toContainText("Warnung 1 von 3");
  await expect(shell).toContainText("3× · alle 60 Sekunden");
});

test("makes unsaved changes explicit and lets the operator discard the draft", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const form = main.getByTestId("config-guided-form");
  const save = main.getByTestId("config-save-button");

  await expect(save).toBeDisabled();
  await form.getByRole("checkbox").first().click();
  await expect(main.getByTestId("config-dirty-indicator")).toHaveText(
    noLeaderFormContract.de.dirty
  );
  await expect(save).toBeEnabled();

  await main.getByTestId("config-reset-button").click();
  await expect(main.getByTestId("config-dirty-indicator")).toHaveCount(0);
  await expect(save).toBeDisabled();
});

test("persists guided changes through the fake save action", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const form = main.getByTestId("config-guided-form");
  const save = main.getByTestId("config-save-button");
  const dryRun = form.getByRole("checkbox").nth(1);
  const wasDryRun = await dryRun.isChecked();

  await dryRun.click();
  await expect(main.getByTestId("config-dirty-indicator")).toBeVisible();
  await save.click();

  await expect(main.getByTestId("config-dirty-indicator")).toHaveCount(0);
  await expect(save).toBeDisabled();
  await expect(
    main.getByText(wasDryRun ? "Aktiv" : "Testbetrieb", { exact: true }).first()
  ).toBeVisible();
  if (wasDryRun) {
    await expect(dryRun).not.toBeChecked();
  } else {
    await expect(dryRun).toBeChecked();
  }
});

test("keeps invalid JSON visible and does not submit it", async ({ page }) => {
  const main = await openDemoPage(page, path);
  await main
    .getByTestId("config-mode-toggle")
    .getByRole("button", { name: noLeaderFormContract.de.tabs[1] })
    .click();

  const editorInput = main
    .getByTestId("config-json-editor")
    .locator('[role="textbox"][aria-label="Editor content"]')
    .first();
  await editorInput.focus();
  await page.keyboard.press("ControlOrMeta+A");
  await page.keyboard.insertText('{"enabled": true');

  await main
    .getByTestId("config-mode-toggle")
    .getByRole("button", { name: noLeaderFormContract.de.tabs[0] })
    .click();

  await expect(main.getByTestId("config-error-summary")).toBeVisible();
  await expect(main.getByTestId("config-error-summary")).toContainText(
    "Ungültiges JSON"
  );
  await expect(main.getByTestId("config-save-button")).toBeDisabled();
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
