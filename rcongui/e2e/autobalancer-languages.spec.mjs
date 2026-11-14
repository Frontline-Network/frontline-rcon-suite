import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

const labels = {
  de: { section: /Spieler informieren/, language: "Nachrichtensprache", german: "Spielernachrichten – Deutsch", english: "Spielernachrichten – Englisch", french: "Spielernachrichten – Französisch", request: "Aufruf für Freiwillige", save: "Einstellungen speichern" },
  en: { section: /Notify players/, language: "Message language", german: "Player messages – German", english: "Player messages – English", french: "Player messages – French", request: "Volunteer request", save: "Save settings" },
  fr: { section: /Informer les joueurs/, language: "Langue des messages", german: "Messages aux joueurs – allemand", english: "Messages aux joueurs – anglais", french: "Messages aux joueurs – français", request: "Demande de volontaires", save: "Enregistrer les paramètres" },
};

for (const language of ["de", "en", "fr"]) {
  test(`Autobalancer has separate editable language packs (${language})`, async ({
    page,
  }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await openDemoPage(page, "/settings/others/autobalancer", { language });
    await page.locator("#autobalancer-settings").click();
    await page
      .getByRole("button", {
        name: labels[language].section,
      })
      .click();
    const select = page.getByRole("combobox", {
      name: labels[language].language,
    });
    await expect(select).toBeVisible();
    await expect(select).toHaveValue("de+en");
    await expect(page.getByText(labels[language].german, { exact: true })).toBeVisible();
    await expect(page.getByText(labels[language].english, { exact: true })).toBeVisible();
    await expect(page.getByText(labels[language].french, { exact: true })).toBeVisible();
    const fields = page.getByRole("textbox", {
      name: labels[language].request,
      exact: true,
    });
    await expect(fields).toHaveCount(3);
    const oldGerman = await fields.nth(0).inputValue();
    const oldFrench = await fields.nth(2).inputValue();
    await fields
      .nth(1)
      .fill(
        "English test: join {target_team} within {seconds} seconds. !balance"
      );
    await fields.nth(1).blur();
    await expect(
      page.getByRole("button", {
        name: labels[language].save,
        exact: true,
      })
    ).toBeEnabled();
    await expect(fields.nth(0)).toHaveValue(oldGerman);
    await expect(fields.nth(2)).toHaveValue(oldFrench);
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
