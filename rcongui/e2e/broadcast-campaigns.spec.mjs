import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

const path = "/settings/broadcast-message";

test("activity-based VIP settings expose translations and suppress one-off trial prompts", async ({ page }) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("campaign-workbench");
  await shell.getByRole("navigation", { name: "Kampagnenbereiche" })
    .getByRole("button", { name: /^VIP-Lebenszyklus/ }).click();
  await shell.getByLabel("Aktivitätsabhängige VIP-Hinweise").check();
  await expect(shell.getByText("Während der aktiven Probe pausiert")).toBeVisible();
  await expect(shell.getByText("Höchstens zwei Angebote in 28 Tagen")).toBeVisible();
  await shell.getByText("Sprachvarianten bearbeiten").first().click();
  const translation = shell.getByLabel("English", { exact: true }).first();
  await translation.fill("Free VIP trial on your phone");
  await expect(translation).toHaveValue("Free VIP trial on your phone");
  await expect(shell.getByTestId("config-dirty-indicator")).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
});

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

test("broadcast intervals use seconds and activity distinguishes acknowledgements", async ({ page }) => {
  const main = await openDemoPage(page, path);
  const shell = main.getByTestId("campaign-workbench");
  const navigation = shell.getByRole("navigation", { name: "Kampagnenbereiche" });
  await navigation.getByRole("button", { name: /^Kampagnen/ }).click();
  await shell.getByText("Neu", { exact: true }).click();
  const interval = shell.getByLabel("Abstand zur nächsten Nachricht (Sekunden)");
  await expect(interval).toHaveValue("900");
  await interval.fill("30");
  await expect(interval).toHaveValue("30");
  await expect(shell.getByText("Bitte eine ganze Zahl von 1 bis 86400 Sekunden angeben.")).toHaveCount(0);
  await navigation.getByRole("button", { name: /^Aktivität/ }).click();
  await expect(shell.getByText("Broadcast-Aktivität", { exact: true })).toBeVisible();
  await expect(shell.getByText(/Eine Serverbestätigung belegt nicht die Anzeige/)).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
});
