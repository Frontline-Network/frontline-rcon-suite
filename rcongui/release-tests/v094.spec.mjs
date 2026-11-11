import { test, expect } from "@playwright/test";

const version = process.env.RELEASE_VERSION;
test.skip(version !== "v0.9.4", "v0.9.4 feature announcement");
const endpoint = "/api/get_update_channel?frontend_version=v0.9.4";
const dialog = (page) => page.getByRole("dialog").filter({ has: page.locator("#release-spotlight-title") });
async function login(context, username) {
  const response = await context.request.post("/api/login", { data: { username, password: "isolated-test-only" } });
  expect(response.status()).toBe(200);
}
async function channel(context) {
  const response = await context.request.get(endpoint);
  expect(response.status()).toBe(200);
  return (await response.json()).result;
}

test("v0.9.4 has its own bilingual announcement instead of the old theme spotlight", async ({ page, context }) => {
  await login(context, "vanguard");
  const result = await channel(context);
  expect(result.highlight_state.release_version).toBe("v0.9.4");
  expect(result.highlight_state.auto_show).toBe(true);
  const release = result.releases.find((r) => r.current);
  expect(release.highlights.title).toEqual({ de: "Neue Belohnungen für eure Community", en: "New rewards for your community" });
  expect(release.highlights.items).toHaveLength(2);
  expect(release.body).not.toContain("crcon-highlights");
  await page.addInitScript(() => localStorage.setItem("crcon.language", "de"));
  await page.goto("/");
  await expect(dialog(page)).toBeVisible();
  await expect(page.locator("#release-spotlight-title")).toHaveText(release.highlights.title.de);
  await dialog(page).getByRole("button", { name: "English", exact: true }).click();
  await expect(page.locator("#release-spotlight-title")).toHaveText(release.highlights.title.en);
  await expect(dialog(page)).toContainText("Preview mode grants no VIP");
  await page.keyboard.press("Escape");
  expect((await channel(context)).highlight_state.seen).toBe(true);
  await page.reload();
  await page.waitForTimeout(2200);
  await expect(dialog(page)).toHaveCount(0);
});

test("old announcement state does not suppress the new v0.9.4 announcement", async ({ page, context }) => {
  await login(context, "upgrade-seen");
  // This fixture account already acknowledged v0.9.0 before the update.
  const state = await channel(context);
  expect(state.highlight_state.release_version).toBe("v0.9.4");
  expect(state.highlight_state.auto_show).toBe(true);
  await page.goto("/");
  await expect(dialog(page)).toBeVisible();
});

test("v0.9.4 rejects mismatched versions and unprotected state changes", async ({ context }) => {
  await login(context, "separate");
  for (const frontend of ["v0.9.3", "v0.9.4-rc.1", "unknown"]) {
    const response = await context.request.get(`/api/get_update_channel?frontend_version=${frontend}`);
    expect((await response.json()).result.highlight_state).toBeNull();
  }
  const response = await context.request.post("/api/set_own_release_highlight_state", { data: { frontend_version: version, release_version: version, action: "claim" } });
  expect(response.status()).toBe(403);
  expect((await channel(context)).highlight_state.auto_show).toBe(true);
});
