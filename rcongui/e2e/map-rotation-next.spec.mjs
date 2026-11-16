import { expect, test } from '@playwright/test';

test('next map marker belongs to the actual position and disappears for an edited draft', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('crcon.language', 'de'));
  await page.goto('/settings/maps/rotation', { waitUntil: 'domcontentloaded' });
  const draft = page.getByTestId('rotation-map-draft');
  const rows = draft.locator('article');
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(1).getByText('Nächste Karte', { exact: true })).toBeVisible();
  await expect(rows.nth(0).getByText('Nächste Karte', { exact: true })).toHaveCount(0);
  await rows.nth(1).getByRole('button', { name: /nach oben|nach oben verschieben|hoch/i }).click();
  await expect(draft.getByText('Nächste Karte', { exact: true })).toHaveCount(0);
});
