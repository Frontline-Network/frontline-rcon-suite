import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

const pages = [
  {
    path: "/settings/others/game-server",
    title: "Gameserver-Verbindung",
    sections: ["Verbindungspool", "Leistungsdiagnose"],
  },
  {
    path: "/settings/others/crcon",
    title: "CRCON-Einstellungen",
    sections: [
      "Identität & Links",
      "Zugriff & Weitergabe",
      "Aktualisierungsraten",
      "Windows-Store-Spieler",
      "Nachrichtenrahmen",
    ],
  },
  {
    path: "/settings/others/steam",
    title: "Steam-API",
    sections: ["Zugangsdaten"],
  },
  {
    path: "/settings/others/log-stream",
    title: "Log-Stream",
    sections: ["Puffer & Start", "Aktualisierung"],
    hasMode: true,
  },
  {
    path: "/settings/others/watch-kill-rate",
    title: "Killrate überwachen",
    sections: [
      "Zeitsteuerung",
      "Schwellenwerte",
      "Ausnahmen",
      "Benachrichtigungen",
    ],
    hasMode: true,
  },
];

for (const configPage of pages) {
  test(`${configPage.title} uses a tailored system form`, async ({ page }) => {
    const runtimeErrors = collectRuntimeErrors(page);
    await page.setViewportSize(VIEWPORTS.desktop);
    const main = await openDemoPage(page, configPage.path);
    const shell = main.getByTestId("config-page-shell");
    const navigation = shell.getByRole("navigation", {
      name: "Konfigurationsbereiche",
    });

    await expect(
      shell.getByRole("heading", { name: configPage.title, exact: true })
    ).toBeVisible();
    await expect(navigation).toBeVisible();
    await expect(shell).not.toContainText(
      "Konfiguriere diesen Bereich sicher über das geführte Formular."
    );
    await expect(shell.getByTestId("config-json-editor")).toHaveCount(0);

    if (configPage.hasMode) {
      await expect(
        shell.getByRole("group", { name: "Betriebsmodus" })
      ).toBeVisible();
    }

    for (const section of configPage.sections) {
      const sectionButton = navigation.getByRole("button", {
        name: new RegExp(`^${section}`),
      });
      await expect(sectionButton).toBeVisible();
      await sectionButton.click();
      await expect(sectionButton).toHaveAttribute("aria-current", "step");
      await expect(
        shell.getByRole("region", { name: section, exact: true })
      ).toBeVisible();
    }

    await expect(shell.getByTestId("config-save-button")).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
    expect(
      runtimeErrors.filter((error) => !error.startsWith("console: Warning:"))
    ).toEqual([]);
  });
}

for (const path of [
  "/settings/others/crcon",
  "/settings/others/watch-kill-rate",
]) {
  test(`${path} stays usable on a narrow viewport`, async ({ page }) => {
    const runtimeErrors = collectRuntimeErrors(page);
    await page.setViewportSize(VIEWPORTS.mobile);
    const main = await openDemoPage(page, path);
    const shell = main.getByTestId("config-page-shell");

    await expect(
      shell.getByRole("navigation", { name: "Konfigurationsbereiche" })
    ).toBeVisible();
    await expect(shell.getByTestId("config-save-button")).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
    expect(
      runtimeErrors.filter((error) => !error.startsWith("console: Warning:"))
    ).toEqual([]);
  });
}
