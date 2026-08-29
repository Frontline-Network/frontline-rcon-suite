import { expect, test } from "@playwright/test";

const openAppearance = async (page) => {
  await page.locator('[data-testid="user-options-menu"]:visible').click();
  await page.getByRole("menuitem", { name: "Darstellung & Farben" }).click();
  await expect(
    page.getByRole("dialog", { name: "Darstellung & Farben" })
  ).toBeVisible();
};

test("admin can preview and persist an account appearance preset", async ({
  page,
}) => {
  await page.goto("/views/live");
  await openAppearance(page);

  await page.getByRole("button", { name: "Tactical Blue" }).click();
  await page.getByRole("radio", { name: /Deuteranopie/ }).check();

  await expect(page.locator("html")).toHaveAttribute(
    "data-theme-preset",
    "tactical-blue"
  );
  await expect(page.locator("html")).toHaveAttribute(
    "data-color-vision",
    "deuteranopia"
  );
  await expect(page.locator("body")).toHaveCSS(
    "background-color",
    "rgb(5, 8, 11)"
  );

  await page.getByRole("button", { name: "Änderungen übernehmen" }).click();
  await expect(page.getByRole("dialog")).toBeHidden();

  await openAppearance(page);
  await expect(
    page.getByRole("button", { name: "Tactical Blue" })
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("radio", { name: /Deuteranopie/ })).toBeChecked();
});

test("admin can save a custom accessible accent color", async ({ page }) => {
  await page.goto("/views/live");
  await openAppearance(page);

  await page.getByLabel("Hex-Farbwert").fill("#7c5cff");
  await expect(page.locator("html")).toHaveAttribute(
    "data-theme-preset",
    "custom"
  );
  await expect(page.locator("html")).toHaveCSS(
    "--template-palette-primary-main",
    "#7c5cff"
  );

  await page.getByRole("button", { name: "Änderungen übernehmen" }).click();
  await openAppearance(page);
  await expect(page.getByLabel("Hex-Farbwert")).toHaveValue("#7c5cff");
});

test("appearance settings stay usable as a mobile full-screen flow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/views/live");
  await page.getByRole("button", { name: "Navigation öffnen" }).click();
  await openAppearance(page);

  const dialog = page.getByRole("dialog", { name: "Darstellung & Farben" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toHaveCSS("height", "844px");
  await expect(dialog.getByRole("button", { name: "Frontline Gold" })).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Änderungen übernehmen" })).toBeVisible();
});
