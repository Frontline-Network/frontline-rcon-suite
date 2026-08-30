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
    section: "Levelgrenzen",
    sectionId: "rules",
  },
  {
    path: "/settings/automods/no-solo-tank",
    title: "Solo-Panzer verhindern",
    section: "Solo-Panzer erkennen",
    sectionId: "detection",
  },
  {
    path: "/settings/others/vac-bans",
    title: "VAC- und Spielsperren prüfen",
    section: "Sperrmaßnahme",
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
    section: "Filterregeln",
    sectionId: "rules",
  },
  {
    path: "/settings/others/seed-vip",
    title: "Seeder-VIP-Belohnung",
    section: "VIP-Belohnung",
    sectionId: "reward",
  },
  {
    path: "/settings/others/expired-vip",
    title: "Abgelaufene VIPs bereinigen",
    section: "Prüfintervall",
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
    const [breadcrumbBox, shellBox] = await Promise.all([
      main.getByRole("navigation", { name: "breadcrumb" }).boundingBox(),
      shell.boundingBox(),
    ]);
    expect(breadcrumbBox).not.toBeNull();
    expect(shellBox).not.toBeNull();
    expect(shellBox.y).toBeGreaterThanOrEqual(
      breadcrumbBox.y + breadcrumbBox.height
    );
    await expect(navigation).toBeVisible();
    await expect(shell.getByRole("complementary").first()).toBeVisible();
    await expect(shell.getByTestId("config-save-button")).toBeVisible();

    const sectionButton = navigation.getByRole("button", {
      name: new RegExp(`^${configPage.section}`),
    });
    await sectionButton.click();
    await expect(sectionButton).toHaveAttribute("aria-current", "step");
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

  await navigation.getByRole("button", { name: /^VIP-Belohnung/ }).click();
  const duration = shell.getByRole("slider", {
    name: "Belohnung pro erfolgreichem Seeding",
  });
  await expect(duration).toBeVisible();
  await expect(shell).not.toContainText(
    "wird im Formular noch nicht unterstützt"
  );

  const originalDuration = Number(await duration.getAttribute("aria-valuenow"));
  await duration.focus();
  await duration.press("ArrowRight");
  await expect(duration).toHaveAttribute(
    "aria-valuenow",
    String(originalDuration + 1)
  );
  await expect(shell.getByTestId("config-dirty-indicator")).toBeVisible();

  await navigation.getByRole("button", { name: /^Ablauf/ }).click();
  await navigation.getByRole("button", { name: /^VIP-Belohnung/ }).click();
  await expect(
    shell.getByRole("slider", {
      name: "Belohnung pro erfolgreichem Seeding",
    })
  ).toHaveAttribute("aria-valuenow", String(originalDuration + 1));
  await expect(shell.getByTestId("config-mode-toggle")).toHaveCount(0);
  await expect(shell.getByTestId("config-json-editor")).toHaveCount(0);
  expect(
    runtimeErrors.filter((error) => !error.startsWith("console: Warning:"))
  ).toEqual([]);
});

test("schema number fields can be cleared and replaced without restoring the old value", async ({
  page,
}) => {
  const main = await openDemoPage(page, "/settings/automods/seeding");
  const shell = main.getByTestId("config-page-shell");

  await shell
    .getByRole("navigation", { name: "Konfigurationsbereiche" })
    .getByRole("button", { name: /^Ausnahmen/ })
    .click();

  const input = shell.getByRole("spinbutton", {
    name: "Spieler bis Level ausnehmen",
  });
  await input.click();
  await input.press("ControlOrMeta+A");
  await input.press("Backspace");
  await page.waitForTimeout(400);
  await expect(input).toHaveValue("");
  await input.pressSequentially("7");
  await page.waitForTimeout(400);
  await expect(input).toHaveValue("7");

  await shell
    .getByRole("navigation", { name: "Konfigurationsbereiche" })
    .getByRole("button", { name: /^Übersicht/ })
    .click();
  await shell
    .getByRole("navigation", { name: "Konfigurationsbereiche" })
    .getByRole("button", { name: /^Ausnahmen/ })
    .click();
  await expect(
    shell.getByRole("spinbutton", { name: "Spieler bis Level ausnehmen" })
  ).toHaveValue("7");
});

for (const { path, modeLabel } of [
  {
    path: "/settings/automods/seeding",
    modeLabel: "Wie soll der Automod laufen?",
  },
  { path: "/settings/others/seed-vip", modeLabel: "Betriebsmodus" },
]) {
  test(`${path} stays usable on a narrow viewport`, async ({ page }) => {
    const runtimeErrors = collectRuntimeErrors(page);
    await page.setViewportSize(VIEWPORTS.mobile);
    const main = await openDemoPage(page, path);
    const shell = main.getByTestId("config-page-shell");

    await expect(shell.getByRole("group", { name: modeLabel })).toBeVisible();
    await expect(shell.getByTestId("config-mode-toggle")).toHaveCount(0);
    await expect(shell.getByTestId("config-json-editor")).toHaveCount(0);
    await expect(shell.getByTestId("config-save-button")).toBeVisible();
    await expect(
      shell.getByRole("navigation", { name: "Konfigurationsbereiche" })
    ).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
    expect(runtimeErrors).toEqual([]);
  });
}
