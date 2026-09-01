import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

const path = "/settings/welcome-message";

for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
  test(`welcome message workbench stays usable on ${viewportName}`, async ({
    page,
  }) => {
    const runtimeErrors = collectRuntimeErrors(page);
    await page.setViewportSize(viewport);
    const main = await openDemoPage(page, path);
    const shell = main.getByTestId("welcome-message-workbench");

    await expect(
      shell.getByRole("heading", {
        name: "Willkommensnachricht",
        exact: true,
      })
    ).toBeVisible();
    await expect(
      shell.getByRole("navigation", {
        name: "Bereiche der Willkommensnachricht",
      })
    ).toBeVisible();
    await expect(shell.getByTestId("welcome-message-input")).toBeVisible();
    await expect(shell.getByTestId("config-save-button")).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
    expect(runtimeErrors).toEqual([]);
  });
}

test("welcome message draft, preview and restore stay in sync", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("welcome-message-workbench");
  const navigation = shell.getByRole("navigation", {
    name: "Bereiche der Willkommensnachricht",
  });
  const input = shell.getByTestId("welcome-message-input");
  const original = await input.inputValue();

  await input.fill(`${original}\nViel Spaß auf dem Server.`);
  await expect(shell.getByTestId("config-dirty-indicator")).toBeVisible();

  await navigation.getByRole("button", { name: /^Vorschau/ }).click();
  await expect(shell).toContainText("Viel Spaß auf dem Server.");

  await shell.getByRole("button", { name: "Alle Server" }).click();
  const dialog = page.getByRole("dialog", {
    name: "Willkommensnachricht auf alle Server anwenden?",
  });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Abbrechen" }).click();

  await shell
    .getByRole("button", { name: "Gespeicherten Text wiederherstellen" })
    .click();
  await navigation.getByRole("button", { name: /^Nachricht/ }).click();
  await expect(shell.getByTestId("welcome-message-input")).toHaveValue(
    original
  );
});

test("empty welcome message is clearly represented as disabled", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("welcome-message-workbench");

  await shell.getByTestId("welcome-message-input").fill("");
  await expect(
    shell.getByText("Deaktiviert", { exact: true }).first()
  ).toBeVisible();
  await expect(shell).toContainText(
    "Ein leerer Text deaktiviert die Willkommensnachricht"
  );
});

test("welcome templates remain available in their focused section", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("welcome-message-workbench");

  await shell.getByRole("button", { name: /^Vorlagen/ }).click();
  await expect(shell.getByLabel("Nachrichtenvorlage auswählen")).toBeVisible();
  await expect(
    shell.getByRole("link", { name: "Vorlage erstellen" })
  ).toBeVisible();
});
