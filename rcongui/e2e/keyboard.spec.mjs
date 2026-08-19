import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

test.describe("keyboard navigation", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("skip link moves focus to the main content", async ({ page }) => {
    await openDemoPage(page, "/");

    await page.keyboard.press("Tab");
    const skipLink = page.getByRole("link", { name: "Zum Hauptinhalt springen" });
    await expect(skipLink).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page.locator("#main-content")).toBeFocused();
  });

  test("Ctrl+K focuses the navigation search", async ({ page }) => {
    await openDemoPage(page, "/");

    await page.keyboard.press("Control+K");
    await expect(page.getByPlaceholder("Navigation durchsuchen …")).toBeFocused();
  });
});

test.describe("mobile navigation", () => {
  test.use({ viewport: VIEWPORTS.mobile });

  test("menu opens and exposes the primary navigation", async ({ page }) => {
    await openDemoPage(page, "/");

    await page.getByRole("button", { name: "Navigation öffnen" }).click();
    const navigation = page.getByRole("navigation", { name: "Hauptnavigation" });
    await expect(navigation).toBeVisible();
    await expect(
      navigation.getByPlaceholder("Navigation durchsuchen …"),
    ).toBeVisible();
  });
});
