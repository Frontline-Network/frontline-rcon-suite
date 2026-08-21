import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { expectNoHorizontalPageOverflow, VIEWPORTS } from "./helpers.mjs";

const protectedLivePaths = new Set([
  "/api/get_connection_info",
  "/api/get_status",
  "/api/get_gamestate",
  "/api/get_server_list",
  "/api/get_ingame_mods",
  "/api/get_online_mods",
  "/api/get_team_view",
]);

for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
  test(`keeps the anonymous login trustworthy at ${viewportName} width`, async ({
    page,
  }, testInfo) => {
    const protectedNetworkRequests = [];
    page.on("request", (request) => {
      const pathname = new URL(request.url()).pathname;
      if (protectedLivePaths.has(pathname)) {
        protectedNetworkRequests.push(pathname);
      }
    });

    await page.setViewportSize(viewport);
    await page.goto("/login?demo_auth=anonymous", {
      waitUntil: "domcontentloaded",
    });

    await expect(page.getByRole("heading", { name: "Anmelden" })).toBeVisible();
    const languageSelector = page.getByRole("button", { name: "Sprache" });
    await expect(languageSelector).toBeVisible();
    await expect(languageSelector.locator("svg")).toBeVisible();
    await expect(page).toHaveTitle("Frontline Network · Anmelden");
    await expectNoHorizontalPageOverflow(page);
    await expect
      .poll(() =>
        page
          .locator("img")
          .evaluateAll((images) =>
            images.every((image) => image.complete && image.naturalWidth > 0)
          )
      )
      .toBe(true);

    const accessibilityResults = await new AxeBuilder({ page }).analyze();
    const blockingViolations = accessibilityResults.violations.filter((item) =>
      ["serious", "critical"].includes(item.impact)
    );
    await testInfo.attach("axe-results", {
      body: JSON.stringify(accessibilityResults, null, 2),
      contentType: "application/json",
    });
    expect(blockingViolations).toEqual([]);

    await page.waitForTimeout(500);
    const protectedApplicationRequests = await page.evaluate(
      () => window.__CRCON_DEMO_PROTECTED_REQUESTS__ ?? []
    );
    expect(protectedNetworkRequests).toEqual([]);
    expect(protectedApplicationRequests).toEqual([]);
    await expect(page).toHaveScreenshot(`login-${viewportName}.png`, {
      fullPage: true,
    });
  });
}

test("redirects an anonymous root entry without protected requests", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.desktop);
  await page.goto("/?demo_auth=anonymous", {
    waitUntil: "domcontentloaded",
  });

  await expect(page).toHaveURL(/\/login\?from=/);
  await expect(page.getByRole("heading", { name: "Anmelden" })).toBeVisible();
  await expect(page).toHaveTitle("Frontline Network · Anmelden");
  await expect
    .poll(() =>
      page.evaluate(() => window.__CRCON_DEMO_PROTECTED_REQUESTS__ ?? [])
    )
    .toEqual([]);
});

test("stops protected polling after an expired session", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.desktop);
  await page.goto("/?demo_auth=expired", { waitUntil: "domcontentloaded" });

  await expect(page).toHaveURL(/\/login\?from=.*session_expired=1/);
  await expect(
    page.getByText("Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.")
  ).toBeVisible();

  await page.waitForTimeout(750);
  const protectedRequests = await page.evaluate(
    () => window.__CRCON_DEMO_PROTECTED_REQUESTS__ ?? []
  );
  expect(
    protectedRequests.filter(
      (path) => path === "/api/get_own_user_permissions"
    )
  ).toHaveLength(1);
});

test("keeps the login form keyboard-operable", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await page.goto("/login?demo_auth=anonymous", {
    waitUntil: "domcontentloaded",
  });

  const username = page.getByLabel("Benutzername");
  const password = page.getByLabel("Passwort");
  const submit = page.getByRole("button", { name: "Anmelden" });

  await username.focus();
  await page.keyboard.press("Tab");
  await expect(password).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(submit).toBeFocused();
  await page.keyboard.press("Enter");

  await expect(
    page.getByText("Der Benutzername ist erforderlich.")
  ).toBeVisible();
  await expect(page.getByText("Das Passwort ist erforderlich.")).toBeVisible();
});
