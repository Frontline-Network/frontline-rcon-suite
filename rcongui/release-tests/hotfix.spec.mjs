import { test, expect } from "@playwright/test";

test.skip(process.env.RELEASE_VERSION !== "v0.9.1", "v0.9.1 hotfix contract");

test("published hotfix notes match the installed version without a new spotlight", async ({ page, context }) => {
  const login = await context.request.post("/api/login", {
    data: { username: "aurora", password: "isolated-test-only" },
  });
  expect(login.status()).toBe(200);
  expect((await login.json()).result).toBe(true);
  expect((await (await context.request.get("/tag_version")).text()).trim()).toBe("v0.9.1");
  const response = await context.request.get("/api/get_update_channel?frontend_version=v0.9.1");
  expect(response.status()).toBe(200);
  const result = (await response.json()).result;
  expect(result.status).toBe("ready");
  expect(result.source).toBe("bundled");
  const release = result.releases.find((item) => item.current);
  expect(release.tag_name).toBe("v0.9.1");
  expect(release.body).toContain("CSRF");
  expect(release.body).toContain("Aurora");
  expect(release.body).toContain("## Deutsch");
  expect(release.body).toContain("## English");
  expect(release.highlights).toBeNull();
  expect(result.highlight_state).toBeNull();
  const mismatched = (await (await context.request.get("/api/get_update_channel?frontend_version=v0.9.0")).json()).result;
  expect(mismatched.releases).toEqual([]);
  expect(mismatched.highlight_state).toBeNull();

  await page.addInitScript(() => localStorage.setItem("crcon.language", "en"));
  await page.goto("/");
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
});
