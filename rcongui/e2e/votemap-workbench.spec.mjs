import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

const routes = [
  {
    path: "/settings/maps/votemap",
    heading: "Aktuelle Auswahl",
  },
  {
    path: "/settings/maps/votemap/whitelist",
    heading: "Kartenpool zusammenstellen",
  },
  {
    path: "/settings/maps/votemap/settings",
    heading: "Abstimmung konfigurieren",
    contentHeading: "Modi & Anzahl",
  },
];

const VOTEMAP_VIEWPORTS = {
  ...VIEWPORTS,
  compact: { width: 320, height: 568 },
  desktop1280: { width: 1280, height: 800 },
};

for (const [viewportName, viewport] of Object.entries(VOTEMAP_VIEWPORTS)) {
  for (const route of routes) {
    test(`${route.heading} stays usable on ${viewportName}`, async ({
      page,
    }) => {
      const runtimeErrors = collectRuntimeErrors(page);
      await page.setViewportSize(viewport);
      const main = await openDemoPage(page, route.path);
      const shell = main.getByTestId("votemap-workbench");

      await expect(
        shell.getByRole("heading", { name: "Kartenabstimmung", exact: true })
      ).toBeVisible();
      await expect(
        shell.getByRole("heading", {
          name: route.contentHeading || route.heading,
          exact: true,
        })
      ).toBeVisible();
      await expect(
        shell.getByRole("tablist", {
          name: "Bereiche der Kartenabstimmung",
        })
      ).toBeVisible();
      await expectNoHorizontalPageOverflow(page);
      expect(runtimeErrors).toEqual([]);
    });
  }
}

test("map pool draft can be changed and restored", async ({ page }) => {
  const main = await openDemoPage(page, "/settings/maps/votemap/whitelist");
  const shell = main.getByTestId("votemap-workbench");

  await shell
    .getByRole("button", { name: "Kursk zum Kartenpool hinzufügen" })
    .click();
  await expect(shell.getByTestId("config-dirty-indicator")).toBeVisible();
  await expect(shell.getByTestId("config-save-button")).toBeEnabled();

  await shell.getByRole("button", { name: "Änderungen zurücksetzen" }).click();
  await expect(shell.getByTestId("config-dirty-indicator")).toBeHidden();
});

test("map catalog stays available when navigating from settings", async ({
  page,
}) => {
  const main = await openDemoPage(page, "/settings/maps/votemap/settings");
  const shell = main.getByTestId("votemap-workbench");

  await shell
    .getByRole("tab", { name: /Kartenpool Auswahl verwalten/ })
    .click();

  await expect(
    shell.getByRole("button", { name: "Kursk zum Kartenpool hinzufügen" })
  ).toBeVisible();
  await expect(
    shell.getByText(
      "Diese Karten-ID ist nicht mehr im Serverkatalog vorhanden.",
      { exact: false }
    )
  ).toHaveCount(0);
});

test("destructive live actions require confirmation", async ({ page }) => {
  const main = await openDemoPage(page, "/settings/maps/votemap");
  const shell = main.getByTestId("votemap-workbench");

  await shell
    .getByRole("button", { name: "Zurücksetzen", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Laufende Abstimmung zurücksetzen?",
  });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Abbrechen" }).click();
});

test("number fields keep an operator draft while typing", async ({ page }) => {
  const main = await openDemoPage(page, "/settings/maps/votemap/settings");
  const shell = main.getByTestId("votemap-workbench");
  const interval = shell.getByRole("spinbutton", {
    name: "Erinnerungsintervall in Minuten",
  });

  await interval.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.press("Backspace");
  await expect(interval).toHaveValue("");
  await page.keyboard.type("25");
  await expect(interval).toHaveValue("25");
  await expect(shell.getByTestId("config-dirty-indicator")).toBeVisible();

  await shell.getByRole("button", { name: "Zurücksetzen" }).click();
  await expect(interval).toHaveValue("20");
});
