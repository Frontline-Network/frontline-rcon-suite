import { expect, test } from '@playwright/test';

test('approximate observations and filter limits are visible in all languages', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/records/players?last_seen_from=2026-01-01T00%3A00%3A00.000Z');
  await expect(page.getByText(/Beobachtungen anderer Server können fehlen/)).toBeVisible();
  await expect(page.getByText(/^etwa /).first()).toBeVisible();
  await page.getByRole('button', { name: 'Listenansicht' }).click();
  await expect(page.getByText(/^etwa /).first()).toBeVisible();

  await page.getByRole('button', { name: 'Sprache', exact: true }).click();
  await page.getByRole('menuitem', { name: 'English', exact: true }).click();
  await expect(page.getByText(/Observations from other servers may be missing/)).toBeVisible();
  await expect(page.getByText(/^about /).first()).toBeVisible();
  await page.getByRole('button', { name: 'Card view' }).click();
  await expect(page.getByText(/^about /).first()).toBeVisible();

  await page.getByRole('button', { name: 'Language', exact: true }).click();
  await page.getByRole('menuitem', { name: 'Français', exact: true }).click();
  await expect(page.getByText(/Les observations des autres serveurs peuvent manquer/)).toBeVisible();
  await expect(page.getByText(/^environ /).first()).toBeVisible();
});
