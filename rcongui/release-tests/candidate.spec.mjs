import { test, expect } from "@playwright/test";

const installed = process.env.RELEASE_VERSION;
test.skip(installed !== "v0.9.3-rc.1", "combined pilot candidate contract");

test("pilot uses exact versions and reviewed bilingual notes without stable spotlight", async ({ page, context }) => {
  const endpoint = `/api/get_update_channel?frontend_version=${installed}`;
  expect((await context.request.get(endpoint)).status()).toBe(401);
  const login = await context.request.post("/api/login", {
    data: { username: "hotfix", password: "isolated-test-only" },
  });
  expect(login.status()).toBe(200);
  expect((await login.json()).result).toBe(true);
  expect((await (await context.request.get("/tag_version")).text()).trim()).toBe(installed);
  const response = await context.request.get(endpoint);
  expect(response.status()).toBe(200);
  const result = (await response.json()).result;
  expect(result.status).toBe("ready");
  expect(result.source).toBe("bundled");
  const current = result.releases.find((entry) => entry.current);
  expect(current.tag_name).toBe(installed);
  expect(current.prerelease).toBe(true);
  for (const text of ["## Deutsch", "## English", "Administration", "RCON3", "RCON4"]) {
    expect(current.body).toContain(text);
  }
  expect(result.highlight_state).toBeNull();
  const mismatch = (await (await context.request.get("/api/get_update_channel?frontend_version=v0.9.2")).json()).result;
  expect(mismatch.releases).toEqual([]);
  expect(mismatch.highlight_state).toBeNull();
  await page.goto("/");
  await expect(page.getByTestId("wardogs-toolbar").getByTestId("global-match-status")).toBeVisible();
  await expect(page.locator("#release-spotlight-title")).toHaveCount(0);
});
