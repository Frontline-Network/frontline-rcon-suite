import { expect, test } from '@playwright/test';
import { collectRuntimeErrors, openDemoPage } from './helpers.mjs';

for (const sample of [
  { language: 'de', rules: /^Regeln/, weapons: /^Waffen begrenzen/, notice: /mindestens eine Minute zurückgehalten/ },
  { language: 'en', rules: /^Rules/, weapons: /^Limit weapons/, notice: /held for at least one minute/ },
  { language: 'fr', rules: /^Règles/, weapons: /^Limiter les armes/, notice: /suspendues pendant au moins une minute/ },
]) {
  test(`weapon event transition is explained in ${sample.language}`, async ({ page }) => {
    const errors = collectRuntimeErrors(page);
    const main = await openDemoPage(page, '/settings/automods/seeding', { language: sample.language });
    const shell = main.getByTestId('config-page-shell');
    await shell.getByRole('navigation').first().getByRole('button', { name: sample.rules }).click();
    await shell.getByRole('button', { name: sample.weapons }).first().click();
    await expect(shell.getByText(sample.notice)).toBeVisible();
    expect(errors).toEqual([]);
  });
}
