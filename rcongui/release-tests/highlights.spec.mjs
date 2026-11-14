import { test, expect } from "@playwright/test";

// The original v0.9.0 spotlight survives hotfixes with the same account key.
const installed = process.env.RELEASE_VERSION || "v0.9.0";
test.skip(!["v0.9.0", "v0.9.1", "v0.9.2", "v0.9.3"].includes(installed), "v0.9.0 spotlight and stable release inheritance contract");

const current = `/api/get_update_channel?frontend_version=${installed}`;
const spotlight = (page) => page.getByRole("dialog").filter({ has: page.locator("#release-spotlight-title") });
async function login(context, username) {
  const response = await context.request.post("/api/login", {
    data: { username, password: "isolated-test-only" },
  });
  expect(response.status()).toBe(200);
  expect((await response.json()).result).toBe(true);
}
async function state(context) {
  const response = await context.request.get(current);
  expect(response.status()).toBe(200);
  return (await response.json()).result;
}
async function reopen(page) {
  await page.getByTestId("user-options-menu").filter({ visible: true }).first().click();
  await page.getByRole("menuitem", { name: /Was ist neu|What.s new/i }).click();
  await expect(spotlight(page)).toBeVisible();
}

test("published metadata, matching versions, authenticated sessions and CSRF", async ({ context }) => {
  expect((await context.request.get(current)).status()).toBe(401);
  await login(context, "separate");
  const result = await state(context);
  expect(result.status).toBe("ready");
  expect(result.source).toBe("bundled");
  expect(result.releases.find((item) => item.current).tag_name).toBe(installed);
  const release = result.releases.find((item) => item.tag_name === "v0.9.0");
  expect(release.tag_name).toBe("v0.9.0");
  expect(release.highlights.title).toEqual({ de: "Dein RCON. Dein Look.", en: "Your RCON. Your style." });
  expect(release.highlights.action.id).toBe("appearance");
  expect(release.body).not.toContain("crcon-highlights");
  expect(result.preview).toBeUndefined();
  expect(result.highlight_state.auto_show).toBe(true);
  expect(result.highlight_state.release_version).toBe("v0.9.0");
  for (const version of ["v0.8.8", "v0.8.9", "v0.9.0", "v0.9.1", "v0.9.2", "v0.9.3", "unknown", "v0.10.0"].filter((value) => value !== installed)) {
    const data = (await (await context.request.get(`/api/get_update_channel?frontend_version=${version}`)).json()).result;
    expect(data.releases).toEqual([]);
    expect(data.highlight_state).toBeNull();
  }
  const rejected = await context.request.post("/api/set_own_release_highlight_state", {
    data: { frontend_version: installed, release_version: "v0.9.0", action: "claim" },
  });
  expect(rejected.status()).toBe(403);
  expect((await state(context)).highlight_state.auto_show).toBe(true);
  // Exercise the same origin/Host split as the shipped nginx proxy, with a
  // genuine session and CSRF cookie, not a CSRF exemption or mocked response.
  const csrf = (await context.cookies()).find((cookie) => cookie.name === "csrftoken").value;
  const viaProxy = await context.request.post("/api/set_own_release_highlight_state", {
    headers: { Host: "backend:8000", Origin: "http://127.0.0.1:8049", "X-CSRFToken": csrf },
    data: { frontend_version: installed, release_version: "v0.9.0", action: "claim" },
  });
  expect(viaProxy.status()).toBe(200);
  expect((await viaProxy.json()).result.show).toBe(true);
});

test("Vanguard: once per account across devices, German/English and manual reopen", async ({ page, context, browser, baseURL }, testInfo) => {
  await login(context, "vanguard");
  await page.addInitScript(() => localStorage.setItem("crcon.language", "de"));
  await page.goto("/");
  await expect(spotlight(page)).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme-preset", "frontline-gold");
  await expect(page.locator("#release-spotlight-title")).toHaveText("Dein RCON. Dein Look.");
  await page.screenshot({ path: testInfo.outputPath("vanguard-de.png") });
  await spotlight(page).getByRole("button", { name: "Français", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "fr");
  await expect(page.locator("#release-spotlight-title")).toHaveText("Your RCON. Your style.");
  await spotlight(page).getByRole("button", { name: "English", exact: true }).click();
  await expect(page.locator("#release-spotlight-title")).toHaveText("Your RCON. Your style.");
  await expect(spotlight(page).getByRole("img")).toHaveAttribute("alt", "RCON dashboards in six Aurora colour styles.");
  await expect.poll(() => spotlight(page).getByRole("img").evaluate((image) => image.complete && image.naturalWidth > 0)).toBe(true);
  await page.keyboard.press("Escape");
  await expect(spotlight(page)).toHaveCount(0);
  expect((await state(context)).highlight_state.seen).toBe(true);
  const otherDevice = await browser.newContext({ baseURL });
  try {
    await login(otherDevice, "vanguard");
    expect((await state(otherDevice)).highlight_state.auto_show).toBe(false);
    const otherPage = await otherDevice.newPage();
    await otherPage.goto("/");
    await otherPage.waitForTimeout(2400);
    await expect(spotlight(otherPage)).toHaveCount(0);
  } finally { await otherDevice.close(); }
  await reopen(page);
  await expect(page.locator("#release-spotlight-title")).toHaveText("Your RCON. Your style.");
});

test("Aurora: later persists for 24 hours and manual action opens appearance", async ({ page, context }, testInfo) => {
  await login(context, "aurora");
  await page.addInitScript(() => localStorage.setItem("crcon.language", "en"));
  await page.goto("/updates");
  await page.waitForTimeout(2200);
  await expect(spotlight(page)).toHaveCount(0); // never automatic on other routes
  await page.goto("/");
  await expect(spotlight(page)).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme-preset", "wardogs");
  await page.screenshot({ path: testInfo.outputPath("aurora-en.png") });
  const before = Date.now();
  await spotlight(page).getByRole("button", { name: /Later/i, exact: true }).click();
  await expect(spotlight(page)).toHaveCount(0);
  const stored = (await state(context)).highlight_state;
  expect(stored.seen).toBe(false);
  expect(stored.auto_show).toBe(false);
  expect(Date.parse(stored.snoozed_until) - before).toBeGreaterThan(86_395_000);
  expect(Date.parse(stored.snoozed_until) - Date.now()).toBeLessThanOrEqual(86_400_000);
  await page.reload();
  await page.waitForTimeout(2400);
  await expect(spotlight(page)).toHaveCount(0);
  await reopen(page);
  expect((await state(context)).highlight_state.snoozed_until).toBeNull();
  await spotlight(page).getByRole("button", { name: "Deutsch", exact: true }).click();
  await expect(page.locator("#release-spotlight-title")).toHaveText("Dein RCON. Dein Look.");
  await page.screenshot({ path: testInfo.outputPath("aurora-de.png") });
  await spotlight(page).getByRole("button", { name: "Darstellung öffnen", exact: true }).click();
  await expect(spotlight(page)).toHaveCount(0);
  await expect(page.getByRole("dialog")).toBeVisible();
});

for (const kind of ["busy", "dialog"]) {
  test(`idle overview waits for ${kind === "busy" ? "focused input" : "another dialog"} to end`, async ({ page, context }) => {
    await login(context, kind);
    // DOM fixtures exercise the production idle guard; API responses are not mocked.
    await page.addInitScript((type) => {
      window.addEventListener("DOMContentLoaded", () => {
        const element = document.createElement(type === "busy" ? "textarea" : "div");
        element.id = "operator-activity-fixture";
        if (type === "dialog") element.setAttribute("role", "dialog");
        document.body.appendChild(element);
        if (type === "busy") element.focus();
      });
    }, kind);
    await page.goto("/");
    await page.waitForTimeout(3000);
    await expect(spotlight(page)).toHaveCount(0);
    expect((await state(context)).highlight_state.auto_show).toBe(true);
    await page.locator("#operator-activity-fixture").evaluate((element) => element.remove());
    await expect(spotlight(page)).toBeVisible();
  });
}
