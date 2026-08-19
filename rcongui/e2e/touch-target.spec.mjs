import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

const expectMinimumTouchTarget = async (locator, label) => {
  const box = await locator.boundingBox();
  expect(box, `${label} has no visible bounding box`).not.toBeNull();
  expect(box.width, `${label} is narrower than 44px`).toBeGreaterThanOrEqual(44);
  expect(box.height, `${label} is shorter than 44px`).toBeGreaterThanOrEqual(44);
};

test("important mobile navigation controls meet the 44px target size", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/");

  const menuButton = page.getByRole("button", { name: "Navigation öffnen" });
  await expectMinimumTouchTarget(menuButton, "mobile menu button");
  await menuButton.click();

  await expectMinimumTouchTarget(
    page.getByRole("combobox", { name: "Server auswählen" }),
    "server selector",
  );
  await expectMinimumTouchTarget(page.getByRole("link", { name: "Übersicht" }), "overview link");
  await expectMinimumTouchTarget(page.getByRole("button", { name: "Schließen" }), "drawer close button");
});
