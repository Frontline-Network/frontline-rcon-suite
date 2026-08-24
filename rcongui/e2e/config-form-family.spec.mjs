import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

const pages = [
  {
    path: "/settings/automods/seeding",
    title: "Seeding-Regeln",
    section: "Regeln",
    sectionId: "rules",
  },
  {
    path: "/settings/automods/level",
    title: "Level-Regeln",
    section: "Regeln",
    sectionId: "rules",
  },
  {
    path: "/settings/automods/no-solo-tank",
    title: "Solo-Panzer verhindern",
    section: "Bestätigen",
    sectionId: "observation",
  },
  {
    path: "/settings/others/vac-bans",
    title: "VAC- und Spielsperren prüfen",
    section: "Maßnahmen",
    sectionId: "actions",
  },
  {
    path: "/settings/others/tk-bans",
    title: "Teamkill-Sperre beim Beitritt",
    section: "Erkennung",
    sectionId: "detection",
  },
  {
    path: "/settings/others/name-kicks",
    title: "Namensfilter",
    section: "Regeln",
    sectionId: "rules",
  },
  {
    path: "/settings/others/seed-vip",
    title: "Seeder-VIP-Belohnung",
    section: "Belohnung",
    sectionId: "reward",
  },
  {
    path: "/settings/others/expired-vip",
    title: "Abgelaufene VIPs bereinigen",
    section: "Zeitplan",
    sectionId: "schedule",
  },
];

for (const configPage of pages) {
  test(`${configPage.title} uses the shared configuration workbench`, async ({
    page,
  }) => {
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
    await expect(
      shell.getByRole("heading", { name: "Zusammenfassung" })
    ).toBeVisible();
    await expect(shell.getByTestId("config-save-button")).toBeVisible();

    await navigation
      .getByRole("button", { name: new RegExp(`^${configPage.section}`) })
      .click();
    await expect(
      shell.getByTestId(`config-section-${configPage.sectionId}`)
    ).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
    expect(runtimeErrors).toEqual([]);
  });
}

test("nested Seeder-VIP settings stay editable in the visual form", async ({
  page,
}) => {
  const runtimeErrors = collectRuntimeErrors(page);
  const main = await openDemoPage(page, "/settings/others/seed-vip");
  const shell = main.getByTestId("config-page-shell");
  const navigation = shell.getByRole("navigation", {
    name: "Konfigurationsbereiche",
  });

  await navigation.getByRole("button", { name: /^Belohnung/ }).click();
  await expect(
    shell.getByText("VIP-Dauer in Tagen", { exact: true }).first()
  ).toBeVisible();
  await expect(shell).not.toContainText(
    "wird im Formular noch nicht unterstützt"
  );

  await shell
    .getByTestId("config-mode-toggle")
    .getByRole("button", { name: "JSON (erweitert)" })
    .click();
  await expect(shell.getByTestId("config-json-editor")).toContainText(
    "vip_days"
  );
  expect(
    runtimeErrors.filter((error) => !error.startsWith("console: Warning:"))
  ).toEqual([]);
});

for (const path of [
  "/settings/automods/seeding",
  "/settings/others/seed-vip",
]) {
  test(`${path} stays usable on a narrow viewport`, async ({ page }) => {
    const runtimeErrors = collectRuntimeErrors(page);
    await page.setViewportSize(VIEWPORTS.mobile);
    const main = await openDemoPage(page, path);
    const shell = main.getByTestId("config-page-shell");

    await expect(shell.getByTestId("config-mode-toggle")).toBeVisible();
    await expect(shell.getByTestId("config-save-button")).toBeVisible();
    await expect(
      shell.getByRole("navigation", { name: "Konfigurationsbereiche" })
    ).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
    expect(runtimeErrors).toEqual([]);
  });
}
