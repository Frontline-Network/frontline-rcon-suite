import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

const path = "/settings/broadcast-message";

for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
  test(`campaign workbench stays usable on ${viewportName}`, async ({
    page,
  }) => {
    const runtimeErrors = collectRuntimeErrors(page);
    await page.setViewportSize(viewport);
    const main = await openDemoPage(page, path);
    const shell = main.getByTestId("campaign-workbench");

    await expect(
      shell.getByRole("heading", { name: "Kampagnen", exact: true })
    ).toBeVisible();
    await expect(
      shell.getByRole("group", { name: "Betriebsart der Kampagnen" })
    ).toBeVisible();
    await expect(
      shell.getByRole("navigation", { name: "Kampagnenbereiche" })
    ).toBeVisible();
    await expect(shell.getByTestId("config-save-button")).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
    expect(runtimeErrors).toEqual([]);
  });
}

test("campaign list keeps one focused editor and confirms deletion", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.desktop);
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("campaign-workbench");
  const navigation = shell.getByRole("navigation", {
    name: "Kampagnenbereiche",
  });

  await navigation.getByRole("button", { name: /^Kampagnen/ }).click();
  await expect(
    shell.getByText("Kampagnenliste", { exact: true })
  ).toBeVisible();
  await expect(shell.getByLabel("Kampagnenname")).toHaveCount(1);

  await shell.getByText("Neu", { exact: true }).click();
  await expect(shell.getByTestId("config-dirty-indicator")).toBeVisible();
  await expect(shell.getByLabel("Kampagnenname")).toHaveValue("");

  await shell.getByRole("button", { name: "Löschen" }).click();
  const dialog = page.getByRole("dialog", { name: "Kampagne löschen?" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Abbrechen" }).click();
  await expect(dialog).toHaveCount(0);
});

test("campaign mode and delivery sections expose the operational controls", async ({
  page,
}) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("campaign-workbench");
  const navigation = shell.getByRole("navigation", {
    name: "Kampagnenbereiche",
  });

  await shell.getByRole("button", { name: "Gemischt" }).click();
  await expect(shell.getByTestId("config-dirty-indicator")).toBeVisible();

  await navigation.getByRole("button", { name: /^Versand/ }).click();
  await expect(shell.getByLabel("Globaler Sendetakt")).toBeVisible();
  await expect(shell.getByLabel("Mindestabstand je Spieler")).toBeVisible();
});
