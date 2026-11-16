import { expect, test } from '@playwright/test';
import { collectRuntimeErrors, openDemoPage } from './helpers.mjs';

for (const sample of [
  { language: 'de', section: /Windows-Store-Spieler/, notice: /Maßnahmen erfordern die bestätigte Plattform PC WinGDK/ },
  { language: 'en', section: /Windows Store players/, notice: /Actions require a confirmed PC WinGDK platform/ },
  { language: 'fr', section: /Les joueurs de Windows Store/, notice: /Les actions exigent la plateforme PC WinGDK confirmée/ },
]) {
  test(`Windows Store rule explains platform verification in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, '/settings/others/crcon', { language: sample.language });
    const shell = main.getByTestId('config-page-shell');
    const navigation = shell.getByRole('navigation').first();
    await navigation.getByRole('button', { name: sample.section }).click();
    await expect(shell.getByText(sample.notice).first()).toBeVisible();
    expect(errors).toEqual([]);
  });
}
