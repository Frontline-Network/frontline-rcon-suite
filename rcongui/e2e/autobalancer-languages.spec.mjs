import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

for (const language of ["de", "en"]) {
  test(`Autobalancer has separate editable language packs (${language})`, async ({
    page,
  }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await openDemoPage(page, "/settings/others/autobalancer", { language });
    await page.locator("#autobalancer-settings").click();
    await page
      .getByRole("button", {
        name: language === "de" ? /Spieler informieren/ : /Notify players/,
      })
      .click();
    const select = page.getByRole("combobox", {
      name: language === "de" ? "Nachrichtensprache" : "Message language",
    });
    await expect(select).toBeVisible();
    await expect(select).toHaveValue("de+en");
    const german =
      language === "de"
        ? "Spielernachrichten – Deutsch"
        : "Player messages – German";
    const english =
      language === "de"
        ? "Spielernachrichten – Englisch"
        : "Player messages – English";
    await expect(page.getByText(german, { exact: true })).toBeVisible();
    await expect(page.getByText(english, { exact: true })).toBeVisible();
    const requestLabel =
      language === "de" ? "Aufruf für Freiwillige" : "Volunteer request";
    const fields = page.getByRole("textbox", {
      name: requestLabel,
      exact: true,
    });
    await expect(fields).toHaveCount(2);
    const oldGerman = await fields.nth(0).inputValue();
    await fields
      .nth(1)
      .fill(
        "English test: join {target_team} within {seconds} seconds. !balance"
      );
    await fields.nth(1).blur();
    await expect(
      page.getByRole("button", {
        name: language === "de" ? "Einstellungen speichern" : "Save settings",
        exact: true,
      })
    ).toBeEnabled();
    await expect(fields.nth(0)).toHaveValue(oldGerman);
    await select.click();
    await select.fill("en");
    await page.getByRole("option", { name: "en", exact: true }).click();
    await expect(select).toHaveValue("en");
    await expectNoHorizontalPageOverflow(page);
  });
}

for (const mode of ["auto", "manual"]) {
  test(`Normal ${mode} dashboard does not treat historical reviews as pending switches`, async ({
    page,
  }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await openDemoPage(page, "/views/autobalancer", { language: "en" });
    await page.locator("#autobalancer-settings").click();
    const modeInput = page.getByRole("combobox", {
      name: "Operating mode",
      exact: true,
    });
    await modeInput.click();
    await modeInput.fill(mode);
    await page.getByRole("option", { name: mode, exact: true }).click();
    await expect(modeInput).toHaveValue(mode);
    await expect(
      page.getByRole("tab", { name: /Review proposals/ })
    ).toHaveCount(0);
    await expect(
      page.getByRole("tab", { name: "Pilot approval", exact: true })
    ).toHaveCount(0);
    await expect(page.getByText("Open proposals", { exact: true })).toHaveCount(
      0
    );
    await expect(
      page.getByText("No confirmed switch in the loaded history", {
        exact: true,
      })
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "History", exact: true })
    ).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
  });
}
