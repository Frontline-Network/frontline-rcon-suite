import { test, expect } from "@playwright/test";

const installed = process.env.RELEASE_VERSION;
test.skip(!["v0.9.1", "v0.9.2"].includes(installed), "hotfix inheritance contract");
const current = `/api/get_update_channel?frontend_version=${installed}`;

test("hotfix preserves unseen feature highlights while keeping the installed changelog", async ({ page, context }) => {
  const login = await context.request.post("/api/login", {
    data: { username: "hotfix", password: "isolated-test-only" },
  });
  expect(login.status()).toBe(200);
  expect((await login.json()).result).toBe(true);
  expect((await (await context.request.get("/tag_version")).text()).trim()).toBe(installed);
  const response = await context.request.get(current);
  expect(response.status()).toBe(200);
  const result = (await response.json()).result;
  expect(result.status).toBe("ready");
  expect(result.source).toBe("bundled");
  const release = result.releases.find((item) => item.current);
  expect(release.tag_name).toBe(installed);
  expect(release.body).toContain(installed === "v0.9.1" ? "CSRF" : "SMTP");
  expect(release.body).toContain("Aurora");
  expect(release.body).toContain("## Deutsch");
  expect(release.body).toContain("## English");
  expect(release.highlights).toBeNull();
  expect(result.highlight_state.release_version).toBe("v0.9.0");
  expect(result.highlight_state.auto_show).toBe(true);
  const mismatched = (await (await context.request.get("/api/get_update_channel?frontend_version=v0.9.0")).json()).result;
  expect(mismatched.releases).toEqual([]);
  expect(mismatched.highlight_state).toBeNull();

  await page.addInitScript(() => localStorage.setItem("crcon.language", "en"));
  await page.goto("/");
  await expect(page.locator("#release-spotlight-title")).toHaveText("Your RCON. Your style.");
  await page.keyboard.press("Escape");
  await expect(page.locator("html")).toHaveAttribute("data-theme-preset", "wardogs");
  const status = page.getByTestId("wardogs-toolbar").getByTestId("global-match-status");
  await expect(status).toBeVisible();
  for (const label of ["Players", "Map", "Remaining"]) {
    await expect(status.getByText(label, { exact: true })).toBeVisible();
  }
  // This isolated server intentionally has no game-server data.
  await expect(status.locator('[data-status-field="players"]')).toContainText("Unknown");
  await expect(status.locator('[data-status-field="time"]')).toContainText("Unknown");
  await expect(page.locator("#release-spotlight-title")).toHaveCount(0);
  await page.goto("/updates");
  await page.getByRole("button", { name: /What.s new/i }).click();
  await expect(page.locator("#release-spotlight-title")).toHaveText("Your RCON. Your style.");
});

for (const username of ["upgrade-seen", "upgrade-later"]) {
  test(`hotfix respects v0.9.0 state saved before upgrade: ${username}`, async ({ page, context }) => {
    expect((await context.request.post("/api/login", {
      data: { username, password: "isolated-test-only" },
    })).status()).toBe(200);
    const read = async () => (await (await context.request.get(current)).json()).result.highlight_state;
    const before = await read();
    expect(before.release_version).toBe("v0.9.0");
    expect(before.seen).toBe(username === "upgrade-seen");
    expect(before.auto_show).toBe(false);
    await page.goto("/");
    await page.waitForTimeout(2400);
    await expect(page.locator("#release-spotlight-title")).toHaveCount(0);
    expect(await read()).toEqual(before);
    await page.getByTestId("user-options-menu").filter({ visible: true }).first().click();
    await page.getByRole("menuitem", { name: /Was ist neu|What.s new/i }).click();
    await expect(page.locator("#release-spotlight-title")).toBeVisible();
    await expect.poll(async () => (await read()).seen).toBe(true);
    expect((await read()).snoozed_until).toBeNull();
  });
}
