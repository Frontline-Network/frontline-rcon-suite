import { expect, test } from '@playwright/test';

for (const mode of ['blocked', 'write-blocked']) {
  test(`player records remain usable when browser storage is ${mode}`, async ({ page }) => {
    await page.addInitScript((mode) => {
      if (mode === 'blocked') {
        Object.defineProperty(window, 'localStorage', {
          get() { throw new DOMException('Storage access denied', 'SecurityError'); },
        });
      } else {
        Storage.prototype.setItem = function () {
          throw new DOMException('Storage write denied', 'QuotaExceededError');
        };
      }
    }, mode);
    const errors = [];
    page.on('pageerror', error => { errors.push(error.message); console.log(error.stack); });
    await page.goto('/records/players', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#main-content')).toBeVisible();
    await expect(page.getByRole('alert').filter({ hasText: 'Browserspeicher ist nicht verfügbar' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sprache', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Sprache', exact: true }).click();
    await page.getByRole('menuitem', { name: 'English', exact: true }).click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.getByRole('alert').filter({ hasText: 'Browser storage is unavailable' })).toBeVisible();
    await page.getByRole('button', { name: 'Language', exact: true }).click();
    await page.getByRole('menuitem', { name: 'Français', exact: true }).click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'fr');
    await expect(page.getByRole('alert').filter({ hasText: 'Le stockage du navigateur est indisponible' })).toBeVisible();
    expect(errors).toEqual([]);
  });
}

test('working browser storage keeps the selected language after reload', async ({ page }) => {
  await page.goto('/records/players', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#main-content')).toBeVisible();
  await page.getByRole('button', { name: 'Sprache', exact: true }).click();
  await page.getByRole('menuitem', { name: 'English', exact: true }).click();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('alert').filter({ hasText: 'Browser storage is unavailable' })).toHaveCount(0);
});
