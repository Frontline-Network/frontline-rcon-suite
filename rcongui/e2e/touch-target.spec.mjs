import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

const expectMinimumTouchTarget = async (locator, label) => {
  const box = await locator.boundingBox();
  expect(box, `${label} has no visible bounding box`).not.toBeNull();
  expect(box.width, `${label} is narrower than 44px`).toBeGreaterThanOrEqual(
    44
  );
  expect(box.height, `${label} is shorter than 44px`).toBeGreaterThanOrEqual(
    44
  );
};

const expectInsideViewport = async (locator, viewport, label) => {
  const box = await locator.boundingBox();
  expect(box, `${label} has no visible bounding box`).not.toBeNull();
  expect(box.x, `${label} starts outside the viewport`).toBeGreaterThanOrEqual(
    0
  );
  expect(
    box.x + box.width,
    `${label} extends beyond the viewport`
  ).toBeLessThanOrEqual(viewport.width);
};

test("the mobile app shell stays within a 320px viewport and keeps navigation available", async ({
  page,
}) => {
  const viewport = { width: 320, height: 720 };
  await page.setViewportSize(viewport);
  await openDemoPage(page, "/");

  await expect(page.getByTestId("global-match-status").first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Navigation öffnen" })
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth
      )
    )
    .toBe(true);

  await page.getByRole("button", { name: "Navigation öffnen" }).click();
  const navigation = page.getByTestId("mobile-command-navigation");
  await expect(navigation).toBeVisible();
  await expect(
    navigation.getByRole("button", { name: "Moderation" })
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth
      )
    )
    .toBe(true);
});

test("important mobile navigation controls meet the 44px target size", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/");

  const menuButton = page.getByRole("button", { name: "Navigation öffnen" });
  const serverSwitcher = page
    .getByTestId("global-server-switcher")
    .filter({ visible: true })
    .first();
  await expectMinimumTouchTarget(menuButton, "mobile menu button");
  await expectMinimumTouchTarget(serverSwitcher, "server selector");
  await menuButton.click();

  const navigation = page.getByTestId("mobile-command-navigation");
  await expectMinimumTouchTarget(
    navigation.getByRole("button", { name: "Übersicht" }),
    "overview workspace"
  );
  await expectMinimumTouchTarget(
    navigation.getByRole("button", { name: "Schließen" }),
    "drawer close button"
  );
  await expectMinimumTouchTarget(
    navigation.getByRole("button", { name: "Sprache" }),
    "language button"
  );
});

for (const [name, viewport] of [
  ["mobile", VIEWPORTS.mobile],
  ["tablet", VIEWPORTS.tablet],
]) {
  test(`important live controls meet the 44px target size on ${name}`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await openDemoPage(page, "/views/live");

    for (const [label, accessibleName] of [
      [`${name} operations tab`, "Einsatz"],
      [`${name} event-log tab`, "Protokoll"],
    ]) {
      const control = page.getByRole("tab", {
        name: accessibleName,
        exact: true,
      });
      await expectMinimumTouchTarget(control, label);
      await expectInsideViewport(control, viewport, label);
    }
    await expectMinimumTouchTarget(
      page.getByRole("button", { name: "Nachricht an alle Spieler" }),
      `${name} message-all control`
    );
  });
}

test("mobile header keeps the brand and current route separate", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/views/live");

  const brand = page.getByTestId("compact-frontline-brand");
  const currentRoute = page.getByTestId("mobile-current-route");
  await expect(currentRoute).toHaveText("Live-Ansicht");

  const brandBox = await brand.boundingBox();
  const routeBox = await currentRoute.boundingBox();
  expect(brandBox).not.toBeNull();
  expect(routeBox).not.toBeNull();
  expect(brandBox.x + brandBox.width).toBeLessThanOrEqual(routeBox.x);
});
